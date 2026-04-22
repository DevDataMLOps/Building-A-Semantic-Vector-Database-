from pyspark.sql import SparkSession
from pyspark.sql.functions import col, coalesce, lit
import os

# Spark Config
spark = SparkSession.builder.appName("VectorEngine").config("spark.sql.shuffle.partitions", "20").config("spark.sql.caseSensitive", "true").config("spark.driver.memory", "4g").config("spark.executor.memory", "4g").master('local[*]').getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

SILVER_PATH = "./data/silver"
os.makedirs(SILVER_PATH, exist_ok=True)

# Ingest the metadata files
print("Reading Metadata file...")
meta_df = spark.read.json("./data/bronze/metadata/*.jsonl.gz")

# select needed columns
meta_clean = meta_df.select(
    col('parent_asin').alias('metadata_parent_asin'),
    col('title'),
    col('main_category'),
    coalesce(col('price'), lit(0.0)).alias("price")
).drop_duplicates(["metadata_parent_asin"])
print(f"Processed {meta_clean.count()} data points")

# Ingest the review files...
review_df = spark.read.json("./data/bronze/review/*.jsonl.gz")

review_clean = review_df.select(
    col("parent_asin"), 
    col("user_id"), 
    col("rating"), 
    col("text"), 
    col("timestamp")
).filter("text IS NOT NULL")
print(f"Processed {review_clean.count()} data points")

# Join
print("Joining datasets...")
silver_join = review_clean.join(
    meta_clean, 
    review_clean.parent_asin == meta_clean.metadata_parent_asin, 
    "inner"
).drop("metadata_parent_asin")

silver_join.coalesce(1).write.mode('overwrite').parquet(f"{SILVER_PATH}/complete_reviews")

print(f"Silver layer is now loaded, {silver_join.count()} data points processed")