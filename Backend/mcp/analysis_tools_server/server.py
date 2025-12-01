import json
from mcp.server.fastmcp import FastMCP
from matplotlib import pyplot as plt 
import pandas as pd
import seaborn as sns
import os
from prophet import Prophet
import boto3 

mcp = FastMCP("analysis-tools" , host="0.0.0.0", port=3040)

# ------------------------
# Utility helpers
# ------------------------

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


def make_filename(title):
    """
    Generate a filesystem-safe filename.

    Arguments:
        title (str): Chart title to use for filename.

    Returns:
        str: Absolute path to the image file.
    """
    return os.path.abspath(f"{title.replace(' ', '_').lower()}.png")


# ------------------------
# Chart Tools
# ------------------------

@mcp.tool()
def create_bar_chart(data: str, x_col: str, y_col: str, title: str) -> str:
    """
    Create a bar chart from a dataset and save as PNG.

    Arguments:
        data (str): JSON string containing the data for the chart.
        x_col (str): Column name for X-axis.
        y_col (str): Column name for Y-axis.
        title (str): Chart title.

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=data, x=x_col, y=y_col)
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


@mcp.tool()
def create_pie_chart(data: str, labels_col: str, values_col: str, title: str) -> str:
    """
    Create a pie chart showing category proportions.

    Arguments:
        data (str): JSON string containing the input data.
        labels_col (str): Column for category labels.
        values_col (str): Column for values.
        title (str): Chart title.

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(8, 8))
    plt.pie(data[values_col], labels=data[labels_col], autopct='%1.1f%%', startangle=140)
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


@mcp.tool()
def create_line_chart(data: str, x_col: str, y_col: str, title: str) -> str:
    """
    Create a line chart showing trends over time.

    Arguments:
        data (str): JSON string containing the input data.
        x_col (str): Column name for X-axis.
        y_col (str): Column name for Y-axis.
        title (str): Chart title.

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=data, x=x_col, y=y_col)
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


@mcp.tool()
def create_scatter_chart(data: str, x_col: str, y_col: str, title: str) -> str:
    """
    Create a scatter plot to visualize relationships between variables.

    Arguments:
        data (str): JSON string containing the input data.
        x_col (str): Column name for X-axis.
        y_col (str): Column name for Y-axis.
        title (str): Chart title.

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=data, x=x_col, y=y_col)
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


@mcp.tool()
def create_histogram(data: str, column: str, title: str, bins: int = 10) -> str:
    """
    Create a histogram showing the distribution of a column.

    Arguments:
        data (str): JSON string containing the input data.
        column (str): Column to plot.
        title (str): Chart title.
        bins (int): Number of bins (default=10).

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(10, 6))
    sns.histplot(data[column], bins=bins, kde=True)
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


@mcp.tool()
def create_box_plot(data: str, x_col: str, y_col: str, title: str) -> str:
    """
    Create a box plot to visualize spread and outliers.

    Arguments:
        data (str): JSON string containing the input data.
        x_col (str): Column for X-axis (category).
        y_col (str): Column for Y-axis (numeric).
        title (str): Chart title.

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=data, x=x_col, y=y_col)
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


@mcp.tool()
def create_heatmap(data: str, title: str) -> str:
    """
    Create a heatmap to visualize correlations between numeric columns.

    Arguments:
        data (str): JSON string containing the input data.
        title (str): Chart title.

    Returns:
        str: Path to saved PNG image.
    """
    data = to_df(data)
    plt.figure(figsize=(10, 8))
    sns.heatmap(data.corr(), annot=True, fmt=".2f", cmap="coolwarm")
    plt.title(title)
    image_path = make_filename(title)
    plt.savefig(image_path)
    plt.close()
    return image_path


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



@mcp.tool()
def upload_photo_s3_get_presigned_url(image_path: str,  object_name: str = None) -> str:
    """
    Upload a file to an S3 bucket and return the S3 object URL.

    Arguments:
        file_path (str): Path to the file to upload.
        bucket_name (str): Name of the S3 bucket.
        object_name (str): S3 object name. If not specified, file_path's basename is used.

    Returns:
        str: URL of the uploaded S3 object.
    """
    if object_name is None:
        object_name = os.path.basename(image_path)

    session = boto3.Session()
    s3 = session.client("s3" , region_name="us-east-1")
    bucket_name =  "synapse-analysis-photos-container"

    s3.upload_file(image_path, bucket_name, object_name)

    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": object_name},
        ExpiresIn=3600  
    )
    try:
        os.remove(image_path)
    except OSError:
        return "Error deleting local file after upload."

    return presigned_url

if __name__ == "__main__":
    mcp.run(transport="sse")