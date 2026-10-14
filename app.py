"""臺北 YouBike 空站觀察：115-1 地理資訊系統運用程式的 App 範本。

執行方式：在終端機輸入 solara run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import solara

DATA_PATH = Path(__file__).parent / "data" / "w3_youbike_long.csv"

# 讀檔放在元件外面：App 啟動時只讀一次，切換選項時不會重新讀檔。
# sno、act 指定為字串，避免被自動轉成整數（W3 的 read_json 陷阱，read_csv 也一樣）。
df = pd.read_csv(DATA_PATH, dtype={"sno": str, "act": str})
df = df[df["act"] == "1"]  # 只看營運中的站

行政區們 = sorted(df["sarea"].unique())
時段們 = sorted(df["時段"].unique())
資料時間們 = sorted(df["snapshot_time"].unique())

# reactive：值改變時，用到它的元件會自動重新執行。
門檻 = solara.reactive(0)
行政區 = solara.reactive(行政區們[0])
時段 = solara.reactive(時段們[0])


def 行政區各時段摘要(資料, 行政區名稱, 門檻值):
    """計算指定行政區各時段的站數、空站比例與車輛總數。"""
    資料 = 資料[資料["sarea"] == 行政區名稱].copy()
    資料["空站"] = 資料["available_rent_bikes"] <= 門檻值
    表 = 資料.groupby("時段").agg(
        總站數=("sno", "nunique"),
        空站數=("空站", "sum"),
        可借車總數=("available_rent_bikes", "sum"),
        可還車總數=("available_return_bikes", "sum"),
    )
    表["空站比例"] = (表["空站數"] / 表["總站數"]).round(3)
    return 表.reset_index()[
        ["時段", "總站數", "空站數", "空站比例", "可借車總數", "可還車總數"]
    ]


def 各區指定時段摘要(資料, 時段值, 門檻值):
    """計算指定時段各行政區的空站比例與車輛數。"""
    資料 = 資料[資料["時段"] == 時段值].copy()
    資料["空站"] = 資料["available_rent_bikes"] <= 門檻值
    表 = 資料.groupby("sarea").agg(
        總站數=("sno", "nunique"),
        空站數=("空站", "sum"),
        可借車總數=("available_rent_bikes", "sum"),
        可還車總數=("available_return_bikes", "sum"),
    )
    表["空站比例"] = (表["空站數"] / 表["總站數"]).round(3)
    return 表.sort_values("空站比例").reset_index()[
        ["sarea", "總站數", "空站數", "空站比例", "可借車總數", "可還車總數"]
    ]


def 行政區空站明細(資料, 行政區名稱, 時段值, 門檻值):
    """列出指定行政區、時段中符合空站門檻的站點。"""
    明細 = 資料[
        (資料["sarea"] == 行政區名稱)
        & (資料["時段"] == 時段值)
        & (資料["available_rent_bikes"] <= 門檻值)
    ]
    明細 = 明細[
        ["時段", "sno", "sna", "ar", "available_rent_bikes", "available_return_bikes"]
    ].rename(
        columns={
            "sno": "站點代碼",
            "sna": "站名",
            "ar": "地址",
            "available_rent_bikes": "可借車數",
            "available_return_bikes": "可還車數",
        }
    )
    return 明細.sort_values(["時段", "可借車數", "站名"]).reset_index(drop=True)


@solara.component
def Page():
    solara.Title("YouBike 空站觀察")
    solara.Markdown("# 臺北 YouBike 各行政區各時段空站比例與車輛數")

    with solara.Column(style={"max-width": "480px"}):
        solara.SliderInt("空站門檻：可借車 ≤", value=門檻, min=0, max=5)
    solara.ToggleButtonsSingle(value=時段, values=時段們)

    各區表 = 各區指定時段摘要(df, 時段.value, 門檻.value)

    圖 = px.bar(
        各區表,
        x="空站比例",
        y="sarea",
        orientation="h",
        title=f"{時段.value}各行政區空站比例（可借車 ≤ {門檻.value} 算空站）",
        labels={"sarea": "行政區", "空站比例": "空站比例"},
        hover_data=["總站數", "空站數", "可借車總數", "可還車總數"],
    )
    圖.update_layout(
        xaxis_tickformat=".0%",
        yaxis={"categoryorder": "total ascending"},
    )
    solara.FigurePlotly(圖)

    solara.DataFrame(各區表)

    solara.Markdown("## 選擇行政區查看詳細資料")
    with solara.Column(style={"max-width": "480px"}):
        solara.Select(label="選擇行政區", value=行政區, values=行政區們)
    表 = 行政區各時段摘要(df, 行政區.value, 門檻.value)

    行政區圖 = px.bar(
        表,
        x="空站比例",
        y="時段",
        orientation="h",
        title=f"{行政區.value}各時段空站比例（可借車 ≤ {門檻.value} 算空站）",
        labels={"時段": "時段", "空站比例": "空站比例"},
        hover_data=["總站數", "空站數", "可借車總數", "可還車總數"],
    )
    行政區圖.update_layout(
        xaxis_tickformat=".0%",
        yaxis={
            "categoryorder": "array",
            "categoryarray": list(reversed(表["時段"].tolist())),
        },
    )
    solara.FigurePlotly(行政區圖)

    solara.DataFrame(表)

    solara.Markdown(f"## {行政區.value}空站站點明細")
    solara.Markdown(
        f"以下列出 {時段.value} 可借車數 ≤ {門檻.value} 的營運中站點。"
    )
    明細 = 行政區空站明細(df, 行政區.value, 時段.value, 門檻.value)
    if 明細.empty:
        solara.Markdown("目前門檻下沒有符合條件的空站。")
    else:
        solara.DataFrame(明細)

    solara.Markdown(
        "資料來源：臺北市 YouBike 2.0 即時資料（臺北市資料大平臺），"
        "依政府資料開放授權條款第 1 版使用。"
    )
    solara.Markdown(f"資料時間（快照）：{'、'.join(資料時間們)}。")
