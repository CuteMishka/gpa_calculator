import io
import random
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

st.set_page_config(page_title="GPA калькуляторы", page_icon="📚", layout="wide")

# ---------------------------
# Көмекші мәндер
# ---------------------------
LETTER_TO_POINTS = {
    "A": 4.0,
    "B": 3.0,
    "C": 2.0,
    "D": 1.0,
    "F": 0.0,
}

EMOJI_MAP = {
    "Математика": "📐",
    "Физика": "⚛️",
    "Химия": "🧪",
    "Биология": "🧬",
    "Тарих": "🏛️",
    "Ағылшын тілі": "📖",
    "Информатика": "💻",
    "География": "🌍",
    "Өнер": "🎨",
    "Қазақ тілі": "✍️",
}

RANDOM_SUBJECTS = [
    "Математика",
    "Физика",
    "Химия",
    "Биология",
    "Тарих",
    "Ағылшын тілі",
    "Информатика",
    "География",
    "Өнер",
    "Қазақ тілі",
]

SCORE_TYPES = ["Әріптік", "Сандық (0-100)"]
PERIODS = ["Q1", "Q2", "Q3", "Q4", "S1", "S2"]


def parse_period(period_raw: str) -> tuple[str, str]:
    value = (period_raw or "").strip().upper()
    if value.startswith("Q"):
        return "Quarter", value
    if value.startswith("S"):
        return "Semester", value
    return "Other", value if value else "N/A"


def score_to_points(score_type: str, score_value: str | float | int) -> float:
    if score_type == "Әріптік":
        return LETTER_TO_POINTS.get(str(score_value).upper(), 0.0)

    numeric = float(score_value)
    if numeric >= 90:
        return 4.0
    if numeric >= 80:
        return 3.0
    if numeric >= 70:
        return 2.0
    if numeric >= 60:
        return 1.0
    return 0.0


def subject_with_emoji(subject: str) -> str:
    s = (subject or "").strip()
    icon = EMOJI_MAP.get(s, "📘")
    return f"{icon} {s}"


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["credits"] = pd.to_numeric(data["credits"], errors="coerce").fillna(0.0)
    data["gpa_points"] = data.apply(
        lambda row: score_to_points(row["score_type"], row["grade"]), axis=1
    )
    data["weighted_points"] = data["gpa_points"] * data["credits"]
    data[["period_type", "period_name"]] = data["period"].apply(parse_period).apply(pd.Series)
    data["subject_display"] = data["subject"].apply(subject_with_emoji)
    return data


def calculate_overall_gpa(data: pd.DataFrame) -> float:
    total_credits = data["credits"].sum()
    if total_credits <= 0:
        return 0.0
    return data["weighted_points"].sum() / total_credits


def generate_random_records(size: int = 6) -> list[dict]:
    records: list[dict] = []
    for subject in random.sample(RANDOM_SUBJECTS, k=min(size, len(RANDOM_SUBJECTS))):
        score_type = random.choice(SCORE_TYPES)
        if score_type == "Әріптік":
            grade = random.choice(["A", "B", "C", "D", "F"])
        else:
            grade = random.randint(55, 100)

        records.append(
            {
                "subject": subject,
                "credits": random.choice([2, 3, 4]),
                "score_type": score_type,
                "grade": grade,
                "period": random.choice(PERIODS),
            }
        )
    return records


def build_pdf_bytes(report_df: pd.DataFrame, student_info: dict) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, page_height = A4
    y = page_height - 40

    # Try to use Arial from Windows to support Cyrillic/Kazakh text.
    font_name = "Helvetica"
    arial_path = Path(r"C:\Windows\Fonts\arial.ttf")
    if arial_path.exists():
        pdfmetrics.registerFont(TTFont("ArialUnicode", str(arial_path)))
        font_name = "ArialUnicode"

    pdf.setTitle("GPA және үлгерім есебі")
    pdf.setFont(font_name, 12)

    lines = [
        "GPA және үлгерім есебі",
        f"Құрастырылған уақыты: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        f"Оқушы: {student_info['name']}",
        f"Сынып: {student_info['class_name']}",
        f"ID: {student_info['student_id']}",
        f"Мектеп: {student_info['school']}",
        f"Оқу жылы: {student_info['academic_year']}",
        "",
        "Пәндер:",
    ]
    lines.extend(
        [
            f"- {row.subject} | Период: {row.period} | Кредит: {row.credits} | Баға: {row.grade}"
            for row in report_df.itertuples(index=False)
        ]
    )

    for line in lines:
        if y < 40:
            pdf.showPage()
            pdf.setFont(font_name, 12)
            y = page_height - 40
        pdf.drawString(40, y, str(line))
        y -= 18

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


# ---------------------------
# Session state
# ---------------------------
if "records" not in st.session_state:
    st.session_state.records = [
        {"subject": "Математика", "credits": 4, "score_type": "Әріптік", "grade": "A", "period": "Q1"},
        {"subject": "Физика", "credits": 3, "score_type": "Сандық (0-100)", "grade": 86, "period": "Q1"},
        {"subject": "Ағылшын тілі", "credits": 2, "score_type": "Әріптік", "grade": "B", "period": "Q2"},
        {"subject": "Тарих", "credits": 2, "score_type": "Сандық (0-100)", "grade": 92, "period": "Q2"},
        {"subject": "Информатика", "credits": 3, "score_type": "Әріптік", "grade": "A", "period": "S1"},
        {"subject": "Биология", "credits": 3, "score_type": "Сандық (0-100)", "grade": 74, "period": "S2"},
    ]

if "student_info" not in st.session_state:
    st.session_state.student_info = {
        "name": "Аружан Сейіт",
        "class_name": "9A",
        "student_id": "ST-2026-014",
        "school": "№12 мектеп-лицей",
        "academic_year": "2025-2026",
    }


# ---------------------------
# UI Header
# ---------------------------
st.title("📚 Оқушының GPA және үлгерім калькуляторы")
st.caption("Clean UI: пәндерді енгізу, GPA есептеу, трендті талдау және есеп экспорттау")


# ---------------------------
# Sidebar input
# ---------------------------
with st.sidebar:
    st.header("👤 Оқушы туралы")
    st.session_state.student_info["name"] = st.text_input("Аты-жөні", value=st.session_state.student_info["name"])
    st.session_state.student_info["class_name"] = st.text_input("Сыныбы", value=st.session_state.student_info["class_name"])
    st.session_state.student_info["student_id"] = st.text_input("Оқушы ID", value=st.session_state.student_info["student_id"])
    st.session_state.student_info["school"] = st.text_input("Мектеп", value=st.session_state.student_info["school"])
    st.session_state.student_info["academic_year"] = st.text_input("Оқу жылы", value=st.session_state.student_info["academic_year"])

    st.divider()
    st.header("➕ Жаңа жазба қосу")

    with st.form("add_record_form", clear_on_submit=True):
        subject = st.text_input("Пән атауы", placeholder="Мысалы: Химия")
        credits = st.number_input("Кредит / сағат", min_value=0.5, max_value=20.0, value=3.0, step=0.5)
        score_type = st.radio("Баға түрі", SCORE_TYPES, horizontal=True)

        if score_type == "Әріптік":
            grade = st.selectbox("Бағасы", ["A", "B", "C", "D", "F"])
        else:
            grade = st.number_input("Бағасы (0-100)", min_value=0, max_value=100, value=85, step=1)

        period = st.selectbox("Период", PERIODS)

        submitted = st.form_submit_button("Сақтау")
        if submitted:
            if not subject.strip():
                st.warning("Пән атауын енгізіңіз.")
            else:
                st.session_state.records.append(
                    {
                        "subject": subject.strip(),
                        "credits": float(credits),
                        "score_type": score_type,
                        "grade": grade,
                        "period": period,
                    }
                )
                st.success("Жазба қосылды.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎲 Деректерді рандомдау", use_container_width=True):
            st.session_state.records = generate_random_records(6)
            st.success("Кездейсоқ деректер жүктелді.")
    with c2:
        if st.button("🧹 Барлығын тазалау", use_container_width=True):
            st.session_state.records = []
            st.info("Барлық жазба өшірілді.")


# ---------------------------
# Build dataframe
# ---------------------------
raw_df = pd.DataFrame(st.session_state.records)

if raw_df.empty:
    st.warning("Дерек жоқ. Сол жақ панель арқылы пәндерді қосыңыз.")
    st.stop()

calc_df = normalize_df(raw_df)
overall_gpa = calculate_overall_gpa(calc_df)


# ---------------------------
# Student card
# ---------------------------
student_info = st.session_state.student_info
st.markdown(
    f"**Оқушы:** {student_info['name']}  |  **Сынып:** {student_info['class_name']}  |  "
    f"**ID:** {student_info['student_id']}  |  **Мектеп:** {student_info['school']}  |  "
    f"**Оқу жылы:** {student_info['academic_year']}"
)


# ---------------------------
# Metrics cards
# ---------------------------
m1, m2, m3 = st.columns(3)
m1.metric("🎯 Жалпы GPA", f"{overall_gpa:.2f}")
m2.metric("📘 Пән саны", f"{calc_df['subject'].nunique()}")
m3.metric("🧾 Жазба саны", f"{len(calc_df)}")


# ---------------------------
# GPA by period
# ---------------------------
period_gpa = (
    calc_df.groupby(["period_type", "period_name"], as_index=False)
    .agg(total_weighted=("weighted_points", "sum"), total_credits=("credits", "sum"))
)
period_gpa["gpa"] = period_gpa.apply(
    lambda r: (r["total_weighted"] / r["total_credits"]) if r["total_credits"] > 0 else 0.0,
    axis=1,
)


# ---------------------------
# Main layout
# ---------------------------
left, right = st.columns([1.25, 1])

with left:
    st.subheader("📋 Үлгерім деректері")
    display_cols = ["subject_display", "credits", "score_type", "grade", "period", "gpa_points"]
    st.dataframe(
        calc_df[display_cols].rename(
            columns={
                "subject_display": "Пән",
                "credits": "Кредит",
                "score_type": "Баға түрі",
                "grade": "Баға",
                "period": "Период",
                "gpa_points": "GPA ұпайы",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

with right:
    st.subheader("📈 Үлгерім тренді")

    order_map = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "S1": 5, "S2": 6}
    trend_df = period_gpa.copy()
    trend_df["order_key"] = trend_df["period_name"].map(order_map).fillna(99)
    trend_df = trend_df.sort_values("order_key")

    trend_df["period_type_kz"] = trend_df["period_type"].replace(
        {"Quarter": "Тоқсан", "Semester": "Семестр", "Other": "Басқа"}
    )

    fig = px.line(
        trend_df,
        x="period_name",
        y="gpa",
        markers=True,
        color="period_type_kz",
        title="Тоқсан және семестр бойынша GPA динамикасы",
        labels={"period_name": "Период", "gpa": "GPA", "period_type_kz": "Период түрі"},
    )
    fig.update_layout(height=380, legend_title_text="Период түрі")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------
# Period summaries
# ---------------------------
st.subheader("🧮 Период бойынша GPA")
s1, s2 = st.columns(2)
with s1:
    q_df = period_gpa[period_gpa["period_type"] == "Quarter"][["period_name", "gpa"]].sort_values("period_name")
    st.write("**Тоқсандар бойынша**")
    if q_df.empty:
        st.info("Тоқсан бойынша дерек жоқ.")
    else:
        st.dataframe(q_df.rename(columns={"period_name": "Тоқсан", "gpa": "GPA"}), hide_index=True)

with s2:
    sem_df = period_gpa[period_gpa["period_type"] == "Semester"][["period_name", "gpa"]].sort_values("period_name")
    st.write("**Семестр бойынша**")
    if sem_df.empty:
        st.info("Семестр бойынша дерек жоқ.")
    else:
        st.dataframe(sem_df.rename(columns={"period_name": "Семестр", "gpa": "GPA"}), hide_index=True)


# ---------------------------
# Export
# ---------------------------
st.subheader("⬇️ Есепті жүктеу")
ex1, ex2 = st.columns(2)

with ex1:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        calc_df.to_excel(writer, sheet_name="Ulgerim", index=False)
        period_gpa.to_excel(writer, sheet_name="Period GPA", index=False)
    excel_buffer.seek(0)

    st.download_button(
        label="Excel есебін жүктеу",
        data=excel_buffer,
        file_name="gpa_esep.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with ex2:
    pdf_bytes = build_pdf_bytes(raw_df, student_info)
    st.download_button(
        label="PDF есебін жүктеу",
        data=pdf_bytes,
        file_name="gpa_esep.pdf",
        mime="application/pdf",
    )


# ---------------------------
# Help
# ---------------------------
with st.expander("ℹ️ Қолдану нұсқаулығы"):
    st.markdown(
        """
1. Сол жақ панельге оқушы мәліметін толтырыңыз.
2. Пән, кредит және баға түрін енгізіп, **Сақтау** батырмасын басыңыз.
3. **🎲 Деректерді рандомдау** батырмасы тестке арналған кездейсоқ деректерді жүктейді.
4. Жоғарғы карточкаларда жалпы GPA мен статистиканы көресіз.
5. **Үлгерім тренді** графигінен динамиканы талдаңыз.
6. Excel немесе PDF форматында есепті жүктеп алыңыз.
"""
    )
