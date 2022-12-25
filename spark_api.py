import plotly.express as px
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from plotly.subplots import make_subplots
import plotly.offline as py
import json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, DateType, TimestampType


spark = SparkSession.builder.appName("flights").getOrCreate()



def load_dataset():
    with open("schema.json","r") as f:
        schema = StructType.fromJson(json.load(f))
    
    
    df = spark.read.csv("data.nosync/cleaned/cleaned_flights.csv",schema=schema, header=True)
    # sample 10% of the data
    df = df.sample(False, 0.1, seed=42)

    return df

# get the unique dates
def get_dates(df):
    dates = df.select("FlightDate").distinct().orderBy("FlightDate", ascending=True).toPandas()["FlightDate"]
    return dates



def matrix_agg(df,x,y,z="count",):
    if z=="count":
        df_aggregated = df.groupBy(x,y).agg({"*": "count"}).withColumnRenamed(f"count(1)", f"{z}_agg")
    else:
        df_aggregated = df.groupBy(x,y).agg({z: "avg"}).withColumnRenamed(f"avg({z})", f"{z}_agg")
    return df_aggregated

def origin_dest_query(df,from_date,to_date,query="ArrDelay"):
    df = df.filter((df["FlightDate"] >= from_date) & (df["FlightDate"] <= to_date))
    if query=="count":
        df = df.groupBy("Origin","Dest").agg({"*": "count"}).withColumnRenamed("count(1)", "count")
    else:
        df = df.groupBy("Origin","Dest").agg({"ArrDelay": "avg"}).withColumnRenamed("avg(ArrDelay)", "ArrDelay")

    # crate a new column with the origin and destination
    df = df.withColumn("Origin-Dest", concat(df["Origin"], lit("-"), df["Dest"]))
    return df


def origin_dest_query(df,from_date,to_date,query="ArrDelay"):
    # filter the dataframe using timestamp from_date and to_date
    df = df.filter(df["FlightDate"].between(from_date,to_date))
    
    if query=="count":
        df = df.groupBy("ORIGIN_STATE","DEST_STATE").agg({"*": "count"}).withColumnRenamed("count(1)", "count")
    else:
        df = df.groupBy("ORIGIN_STATE","DEST_STATE").agg({"ArrDelay": "avg"}).withColumnRenamed("avg(ArrDelay)", "ArrDelay")

    # crate a new column with the origin and destination
    # order by query, descendant order
    df = df.orderBy(df[query].desc())

    return df

def routes_queries(df,date_start,date_end,origin="BOS",query="NumFlights",scope="airports"):
    df_aggregated = df.filter((col("Origin") == origin))
    df_aggregated = df_aggregated.filter((col("FlightDate") >= date_start) & (col("FlightDate") <= date_end))
    # aggregate by flight date, day of weew, Origin and Dest, count the number of flights and average the arrival delay
    if scope == "airports":
        df_aggregated = df_aggregated.groupBy("Origin","Dest","ORIGIN_LATITUDE","ORIGIN_LONGITUDE","DEST_LATITUDE","DEST_LONGITUDE").agg({"ArrDelay": "avg","*":"count"}).withColumnRenamed("avg(ArrDelay)", "AverageArrivalDelay").withColumnRenamed("count(1)", "NumFlights")
    else:
        df_aggregated = df_aggregated.groupBy("ORIGIN_STATE","DEST_STATE").agg({"ArrDelay": "avg","*":"count","ORIGIN_LATITUDE":"avg","DEST_LATITUDE":"avg","ORIGIN_LONGITUDE":"avg","DEST_LONGITUDE":"avg"}).withColumnRenamed("avg(ArrDelay)", "AverageArrivalDelay").withColumnRenamed("count(1)", "NumFlights")
        # rename columns
        df_aggregated = df_aggregated.withColumnRenamed("avg(ORIGIN_LATITUDE)", "ORIGIN_LATITUDE").withColumnRenamed("avg(ORIGIN_LONGITUDE)", "ORIGIN_LONGITUDE").withColumnRenamed("avg(DEST_LATITUDE)", "DEST_LATITUDE").withColumnRenamed("avg(DEST_LONGITUDE)", "DEST_LONGITUDE")

    # sort by query and take the first 100 rows
    df_aggregated = df_aggregated.orderBy(df_aggregated[query].desc()).limit(100)
    return df_aggregated