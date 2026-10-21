"""臺北 YouBike 空站觀察：115-1 地理資訊系統運用程式的 App 範本。

執行方式：在終端機輸入 solara run app.py
"""

import html
from pathlib import Path

import ipyleaflet
import ipywidgets
import leafmap
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

級距順序 = ["0 輛", "1–3 輛", "4–6 輛", "7–10 輛", "11 輛以上"]
級距顏色 = {
    "0 輛": "#00224e",
    "1–3 輛": "#3b496c",
    "4–6 輛": "#707173",
    "7–10 輛": "#c3b369",
    "11 輛以上": "#fee838",
    "無資料": "#808080",
}

# reactive：值改變時，用到它的元件會自動重新執行。
門檻 = solara.reactive(0)
行政區 = solara.reactive(行政區們[0])
時段 = solara.reactive(時段們[0])


def 可借車級距(車數):
    """依可借車數回傳地圖與圖表使用的顏色級距。"""
    if pd.isna(車數) or 車數 < 0:
        return "無資料"
    if 車數 == 0:
        return "0 輛"
    if 車數 <= 3:
        return "1–3 輛"
    if 車數 <= 6:
        return "4–6 輛"
    if 車數 <= 10:
        return "7–10 輛"
    return "11 輛以上"


def 指定行政區時段站點(資料, 行政區名稱, 時段值):
    """取得目前選定行政區與時段的所有營運站點，不套用空站門檻。"""
    站點 = 資料[
        (資料["sarea"] == 行政區名稱) & (資料["時段"] == 時段值)
    ].copy()
    站點["可借車級距"] = 站點["available_rent_bikes"].apply(可借車級距)
    return 站點


def 建立站點地圖(站點):
    """建立以可借車數級距著色的互動式站點地圖。"""
    有座標站點 = 站點.dropna(subset=["latitude", "longitude"])
    if 有座標站點.empty:
        return None, len(站點)

    中心 = [
        有座標站點["latitude"].mean(),
        有座標站點["longitude"].mean(),
    ]
    地圖 = leafmap.Map(
        center=中心,
        zoom=13,
        height="440px",
        width="100%",
        basemap="OpenStreetMap",
    )
    緯度界線 = [有座標站點["latitude"].min(), 有座標站點["latitude"].max()]
    經度界線 = [有座標站點["longitude"].min(), 有座標站點["longitude"].max()]
    if len(有座標站點) > 1 and (
        緯度界線[0] != 緯度界線[1] or 經度界線[0] != 經度界線[1]
    ):
        地圖.fit_bounds(
            [
                [緯度界線[0], 經度界線[0]],
                [緯度界線[1], 經度界線[1]],
            ]
        )
    elif len(有座標站點) == 1:
        地圖.zoom = 16

    for _, 站 in 有座標站點.iterrows():
        車數 = 站["available_rent_bikes"]
        車數文字 = "資料缺漏" if pd.isna(車數) else f"{int(車數)} 輛"
        站名 = html.escape(str(站["sna"]))
        popup = ipywidgets.HTML(
            value=f"<b>站名：</b>{站名}<br><b>可借車數：</b>{車數文字}"
        )
        地圖.add(
            ipyleaflet.CircleMarker(
                location=(站["latitude"], 站["longitude"]),
                radius=7,
                color="#ffffff",
                weight=2,
                fill_color=級距顏色[站["可借車級距"]],
                fill_opacity=0.9,
                title=str(站["sna"]),
                popup=popup,
            )
        )

    圖例 = {級距: 級距顏色[級距] for 級距 in 級距順序}
    if "無資料" in 有座標站點["可借車級距"].values:
        圖例["無資料"] = 級距顏色["無資料"]
    地圖.add_legend(
        title="可借車數",
        legend_dict=圖例,
        position="bottomright",
    )
    return 地圖, len(站點) - len(有座標站點)


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

    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column():
            solara.SliderInt("空站門檻：可借車 ≤", value=門檻, min=0, max=5)
        with solara.Column():
            solara.Select(label="選擇行政區", value=行政區, values=行政區們)
    solara.ToggleButtonsSingle(value=時段, values=時段們)

    站點 = 指定行政區時段站點(df, 行政區.value, 時段.value)
    地圖, 無座標站數 = 建立站點地圖(站點)
    solara.Markdown(f"## {行政區.value}・{時段.value}站點分布")
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column():
            if 地圖 is None:
                solara.Markdown("目前選擇的時段沒有可繪製座標的站點。")
            else:
                solara.display(地圖)
                if 無座標站數:
                    solara.Markdown(
                        f"有 {無座標站數} 個站點因缺少座標，未顯示於地圖。"
                    )
            solara.Markdown(
                "地圖底圖來源：[OpenStreetMap 貢獻者]"
                "(https://www.openstreetmap.org/copyright)。"
            )
        with solara.Column():
            站點級距表 = (
                站點["可借車級距"]
                .value_counts()
                .reindex(
                    級距順序
                    + (["無資料"] if "無資料" in 站點["可借車級距"].values else []),
                    fill_value=0,
                )
                .rename_axis("可借車數級距")
                .reset_index(name="站點數")
            )
            站點圖 = px.bar(
                站點級距表,
                x="可借車數級距",
                y="站點數",
                color="可借車數級距",
                category_orders={
                    "可借車數級距": 站點級距表["可借車數級距"].tolist()
                },
                color_discrete_map=級距顏色,
                title=f"{行政區.value}・{時段.value}各級距站點數",
                labels={"可借車數級距": "可借車數", "站點數": "站點數"},
            )
            站點圖.update_layout(
                showlegend=False,
                xaxis={
                    "categoryorder": "array",
                    "categoryarray": 站點級距表["可借車數級距"].tolist(),
                },
                margin={"l": 20, "r": 20, "t": 60, "b": 20},
            )
            solara.FigurePlotly(站點圖)

    各區表 = 各區指定時段摘要(df, 時段.value, 門檻.value)
    各區顯示表 = 各區表.assign(
        選定狀態=各區表["sarea"].apply(
            lambda 名稱: "目前選定行政區" if 名稱 == 行政區.value else "其他行政區"
        )
    )

    圖 = px.bar(
        各區顯示表,
        x="空站比例",
        y="sarea",
        orientation="h",
        color="選定狀態",
        color_discrete_map={
            "目前選定行政區": "#e76f51",
            "其他行政區": "#90a4ae",
        },
        title=f"{時段.value}各行政區空站比例（可借車 ≤ {門檻.value} 算空站）",
        labels={"sarea": "行政區", "空站比例": "空站比例"},
        hover_data=["總站數", "空站數", "可借車總數", "可還車總數"],
    )
    圖.update_layout(
        xaxis_tickformat=".0%",
        yaxis={"categoryorder": "total ascending"},
    )
    表 = 行政區各時段摘要(df, 行政區.value, 門檻.value)
    行政區顯示表 = 表.assign(
        選定狀態=表["時段"].apply(
            lambda 名稱: "目前選定時段" if 名稱 == 時段.value else "其他時段"
        )
    )

    行政區圖 = px.bar(
        行政區顯示表,
        x="空站比例",
        y="時段",
        orientation="h",
        color="選定狀態",
        color_discrete_map={
            "目前選定時段": "#e76f51",
            "其他時段": "#90a4ae",
        },
        title=(
            f"{行政區.value}各時段空站比例"
            f"（選定時段：{時段.value}，可借車 ≤ {門檻.value} 算空站）"
        ),
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
    with solara.ColumnsResponsive(12, medium=6):
        with solara.Column():
            solara.FigurePlotly(圖)
            solara.DataFrame(各區顯示表)
        with solara.Column():
            solara.Markdown(f"## {行政區.value}各時段摘要")
            solara.FigurePlotly(行政區圖)
            solara.DataFrame(行政區顯示表)

    solara.Markdown("### 目前選定時段的營運站點")
    站點明細 = 站點[["sna", "available_rent_bikes"]].rename(
        columns={"sna": "站名", "available_rent_bikes": "可借車數"}
    )
    站點明細 = 站點明細.sort_values(["可借車數", "站名"])
    solara.DataFrame(站點明細)

    solara.Markdown(f"### {行政區.value}空站站點明細")
    solara.Markdown(f"以下列出 {時段.value} 可借車數 ≤ {門檻.value} 的營運中站點。")
    明細 = 行政區空站明細(df, 行政區.value, 時段.value, 門檻.value)
    if 明細.empty:
        solara.Markdown("目前門檻下沒有符合條件的空站。")
    else:
        solara.DataFrame(明細)

    solara.Markdown(
        "資料來源：臺北市 YouBike 2.0 即時資料（臺北市資料大平臺），"
        "依政府資料開放授權條款第 1 版使用。"
    )
    快照時間們 = sorted(站點["snapshot_time"].dropna().astype(str).unique())
    solara.Markdown(
        f"資料時間（目前選定時段快照）：{'、'.join(快照時間們) or '無資料'}。"
    )
