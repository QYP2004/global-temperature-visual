import os
from typing import Optional

import pandas as pd


class DataEngine:
    def __init__(self, data_path: Optional[str] = None) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 拿到当前文件的绝对路径
        self.path: str = (
            data_path if data_path is not None else os.path.join(base_dir, "dataset")
        )

    @staticmethod
    def _normalize_country_name(name: str) -> str:
        return str(name).strip().lower()

    def _get_file_path(self, filename: str) -> str:
        if not filename:
            raise ValueError("find filename can't be null")

        if os.path.isabs(filename):
            return filename

        in_data_dir = os.path.join(self.path, filename)
        if os.path.exists(in_data_dir):
            return in_data_dir

        return in_data_dir

    def _load_csv(self, filename: str) -> pd.DataFrame:
        file_path = self._get_file_path(filename)

        try:
            df = pd.read_csv(file_path)  # get dataFrame
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"文件不存在: {file_path}\n请确认数据目录是否正确（当前 data_path: {self.path}）。"
            ) from e
        except Exception as e:
            raise RuntimeError(f"读取 CSV 失败: {file_path}\n错误: {e}") from e

        df["year"] = pd.to_datetime(
            df["dt"], errors="coerce"
        ).dt.year  # 将具体日期转换成年
        return df

    def get_global_temp(self, min_year: int = 1850) -> pd.DataFrame:
        """处理全球总温数据（按年平均）。返回列：year, temperature"""
        df = self._load_csv("GlobalTemperatures.csv")

        filtered = df.loc[
            df["year"] >= min_year, ["year", "LandAverageTemperature"]
        ]  # 只保留年份大于等于 min_year 的year, LandAverageTemperature两行
        filtered = filtered.dropna()  # 有缺失值（NaN）的行删掉
        grouped = (
            filtered.groupby("year", as_index=False)["LandAverageTemperature"]
            .mean()  # 对每年温度取平均值
            .rename(columns={"LandAverageTemperature": "temperature"})
            .sort_values("year")
            .reset_index(drop=True)
        )

        grouped["year"] = grouped["year"].astype("int32")
        grouped["temperature"] = grouped["temperature"].astype("float64")
        return grouped

    def get_city_temp_by_year(self, year: int, limit: int = 20) -> pd.DataFrame:
        """按年份计算各城市平均温度，返回列：City, temperature"""
        df = self._load_csv("GlobalLandTemperaturesByCity.csv")

        filtered = df.loc[
            (df["year"] == year) & df["AverageTemperature"].notna(),
            ["City", "AverageTemperature"],
        ]
        if filtered.empty:
            return filtered.assign(temperature=pd.Series(dtype="float64"))

        grouped = (
            filtered.groupby("City", as_index=False)["AverageTemperature"]
            .mean()
            .rename(columns={"AverageTemperature": "temperature"})
            .sort_values("temperature", ascending=False)
            .head(limit)
            .reset_index(drop=True)
        )

        grouped["temperature"] = grouped["temperature"].astype("float64")
        return grouped

    def get_state_temp_by_year(self, year: int, country: str, limit: int = 15) -> pd.DataFrame:
        """按年份和国家计算各州/省平均温度，返回列：State, temperature"""
        df = self._load_csv("GlobalLandTemperaturesByState.csv")

        filtered = df.loc[
            (df["year"] == year)
            & (df["Country"] == country)
            & df["AverageTemperature"].notna(),
            ["State", "AverageTemperature"],
        ]
        if filtered.empty:
            return filtered.assign(temperature=pd.Series(dtype="float64"))

        grouped = (
            filtered.groupby("State", as_index=False)["AverageTemperature"]
            .mean()
            .rename(columns={"AverageTemperature": "temperature"})
            .sort_values("temperature", ascending=False)
            .head(limit)
            .reset_index(drop=True)
        )

        grouped["temperature"] = grouped["temperature"].astype("float64")
        return grouped


if __name__ == "__main__":
    engine = DataEngine()
    try:
        global_temp = engine.get_global_temp()

        print("全球温度年数据预览:")
        print(global_temp.head())

    except Exception as e:
        print(f"运行失败: {e}")
