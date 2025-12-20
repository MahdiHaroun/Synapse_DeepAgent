import json
from mcp.server.fastmcp import FastMCP
from matplotlib import pyplot as plt 
import pandas as pd
import seaborn as sns
import os
from prophet import Prophet
import boto3 
import io
from dotenv import load_dotenv
import os
from pathlib import Path

mcp = FastMCP("analysis-tools" , host="0.0.0.0", port=3040)



#load_dotenv("/app/.env")
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")
os.environ["AWS_DEFAULT_REGION"] = os.getenv("AWS_DEFAULT_REGION")




def to_df(data):
    """
    Convert input data into a Pandas DataFrame.

    Arguments:
        data (DataFrame | list | dict | str): Input data to convert.

    Returns:
        pd.DataFrame: Converted DataFrame.
    """
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON string provided for data")
    
    if isinstance(data, pd.DataFrame):
        return data
    elif isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, dict):
        return pd.DataFrame(data)
    else:
        raise ValueError("Unsupported data format. Must be DataFrame, list, dict, or JSON string.")







@mcp.tool()
def create_bar_chart(thread_id: str, data: str, x_col: str, y_col: str, title: str) -> dict:
    """
    Create a bar chart in memory, upload directly to S3 under bucket/thread_id/,
    and return a presigned URL.
    """
    # Convert JSON → DataFrame
    df = to_df(data)

    # Create in-memory buffer
    img_buffer = io.BytesIO()

    # Plot
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df, x=x_col, y=y_col)
    plt.title(title)

    # Save directly to buffer (PNG)
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()

    # Reset buffer pointer
    img_buffer.seek(0)

    # Prepare S3 client
    s3 = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "synapse-openapi-schemas"

    # Filename for S3
    filename = f"{title.replace(' ', '_')}_bar_chart.png"
    s3_key = f"{thread_id}/{filename}"

    # Upload from in-memory buffer
    s3.upload_fileobj(img_buffer, bucket_name, s3_key)

    # Generate presigned URL
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=3600
    )

    return {
        "presigned_url": presigned_url,
        "s3_key": s3_key
    }



@mcp.tool()
def create_pie_chart(thread_id: str, data: str, labels_col: str, values_col: str, title: str) -> dict:
    """
    Create a pie chart in memory, upload directly to S3 under bucket/thread_id/,
    and return a presigned URL.
    """
    # Convert JSON to DataFrame
    df = to_df(data)

    # Create in-memory buffer
    img_buffer = io.BytesIO()

    # Plot pie chart
    plt.figure(figsize=(8, 8))
    plt.pie(df[values_col], labels=df[labels_col], autopct='%1.1f%%', startangle=140)
    plt.title(title)

    # Save directly to buffer (PNG)
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()

    # Reset buffer pointer
    img_buffer.seek(0)

    # Prepare S3 client
    s3 = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "synapse-openapi-schemas"

    # S3 key with thread_id
    filename = f"{title.replace(' ', '_')}_pie_chart.png"
    s3_key = f"{thread_id}/{filename}"

    # Upload in-memory buffer to S3
    s3.upload_fileobj(img_buffer, bucket_name, s3_key)

    # Generate presigned URL
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=3600
    )

    return {
        "presigned_url": presigned_url,
        "s3_key": s3_key
    }


@mcp.tool()
def create_line_chart(thread_id: str, data: str, x_col: str, y_col: str, title: str) -> dict:
    """
    Create a line chart in memory, upload directly to S3 under bucket/thread_id/,
    and return a presigned URL.
    """
    # Convert JSON string to DataFrame
    df = to_df(data)

    # Create in-memory buffer
    img_buffer = io.BytesIO()

    # Plot line chart
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=df, x=x_col, y=y_col)
    plt.title(title)

    # Save plot to in-memory buffer
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()

    # Reset buffer pointer
    img_buffer.seek(0)

    # Prepare S3 client
    s3 = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "synapse-openapi-schemas"

    # S3 key with thread_id
    filename = f"{title.replace(' ', '_')}_line_chart.png"
    s3_key = f"{thread_id}/{filename}"

    # Upload from in-memory buffer
    s3.upload_fileobj(img_buffer, bucket_name, s3_key)

    # Generate presigned URL
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": s3_key},
        ExpiresIn=3600
    )

    return {
        "presigned_url": presigned_url,
        "s3_key": s3_key
    }



@mcp.tool()
def create_scatter_chart(thread_id: str, data: str, x_col: str, y_col: str, title: str) -> dict:
    """
    Create a scatter chart in memory, upload directly to S3 under bucket/thread_id/,
    and return a presigned URL.
    """

    df = to_df(data)

    img_buffer = io.BytesIO()
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x=x_col, y=y_col)
    plt.title(title)
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()
    img_buffer.seek(0)

    s3 = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "synapse-openapi-schemas"
    filename = f"{title.replace(' ', '_')}_scatter_chart.png"
    s3_key = f"{thread_id}/{filename}"
    s3.upload_fileobj(img_buffer, bucket_name, s3_key)

    presigned_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": s3_key}, ExpiresIn=3600
    )
    return {"presigned_url": presigned_url, "s3_key": s3_key}

@mcp.tool()
def create_histogram(thread_id: str, data: str, column: str, title: str, bins: int = 10) -> dict:
    """
    Create a histogram in memory, upload directly to S3 under bucket/thread_id/,
    and return a presigned URL.
    """
    df = to_df(data)
    
    img_buffer = io.BytesIO()
    plt.figure(figsize=(10, 6))
    sns.histplot(df[column], bins=bins, kde=True)
    plt.title(title)
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()
    img_buffer.seek(0)

    s3 = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "synapse-openapi-schemas"
    filename = f"{title.replace(' ', '_')}_histogram.png"
    s3_key = f"{thread_id}/{filename}"
    s3.upload_fileobj(img_buffer, bucket_name, s3_key)

    presigned_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": s3_key}, ExpiresIn=3600
    )
    return {"presigned_url": presigned_url, "s3_key": s3_key}




@mcp.tool()
def create_box_plot(thread_id: str, data: str, x_col: str, y_col: str, title: str) -> dict:
    """
    Create a box plot in memory, upload directly to S3 under bucket/thread_id/,
    and return a presigned URL.
    """
    df = to_df(data)
    

    img_buffer = io.BytesIO()
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x=x_col, y=y_col)
    plt.title(title)
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()
    img_buffer.seek(0)

    s3 = boto3.client("s3", region_name="eu-central-1")
    bucket_name = "synapse-openapi-schemas"
    filename = f"{title.replace(' ', '_')}_box_plot.png"
    s3_key = f"{thread_id}/{filename}"
    s3.upload_fileobj(img_buffer, bucket_name, s3_key)

    presigned_url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": bucket_name, "Key": s3_key}, ExpiresIn=3600
    )
    return {"presigned_url": presigned_url, "s3_key": s3_key}






@mcp.tool()
def top_products(data, date_col, product_col, freq="M", top_k=5):
    """
    Return top-selling products per period (e.g., per month).

    Arguments:
        data (list|dict|DataFrame): Input data.
        date_col (str): Column name for datetime.
        product_col (str): Column name for product.
        freq (str): Grouping frequency (default='M').
        top_k (int): Number of top products to return.

    Returns:
        dict: Mapping of period -> top products and counts.
    """
    df = to_df(data)
    df[date_col] = pd.to_datetime(df[date_col])
    grouped = df.groupby([pd.Grouper(key=date_col, freq=freq), product_col]).size()

    result = {}
    for date, frame in grouped.groupby(level=0):
        sorted_p = frame.sort_values(ascending=False)
        result[str(date.date())] = sorted_p.head(top_k).to_dict()

    return result


@mcp.tool()
def forecast_prophet(data, steps: int = 1):
    """
    Forecast next future values using Prophet.
    
    Input must contain a date column 'ds' and a value column 'y'.
    """
    df = to_df(data).copy()
    df["ds"] = pd.to_datetime(df["ds"], errors="coerce")
    df = df.dropna(subset=["ds", "y"])

    model = Prophet()
    model.fit(df)

    future = model.make_future_dataframe(periods=steps, freq="M")
    forecast = model.predict(future)

    return forecast.tail(steps)[["ds", "yhat", "yhat_lower", "yhat_upper"]].to_dict(orient="records")





    

if __name__ == "__main__":
    mcp.run(transport="sse")