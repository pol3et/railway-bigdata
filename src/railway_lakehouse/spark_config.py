"""Shared optional Spark runtime package coordinates."""

DELTA_SPARK_MAVEN_PACKAGE = "io.delta:delta-spark_4.1_2.13:4.1.0"
SPARK_S3A_HADOOP_AWS_PACKAGE = "org.apache.hadoop:hadoop-aws:3.4.1"
SPARK_S3A_AWS_SDK_BUNDLE_PACKAGE = "software.amazon.awssdk:bundle:2.24.6"
SPARK_S3A_PACKAGES = ",".join(
    [SPARK_S3A_HADOOP_AWS_PACKAGE, SPARK_S3A_AWS_SDK_BUNDLE_PACKAGE]
)
