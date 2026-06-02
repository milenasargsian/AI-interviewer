"""Lightweight localization for the UI (English / Armenian / Russian).

UI strings are looked up with ``t(key)``. The *interview content* language
(questions, feedback) is handled separately via prompt directives in
``llm_client.lang_directive``.
"""

import streamlit as st

# Display name -> language code. Display names are shown in the selector.
LANGUAGES = {
    "English": "en",
    "Հայերեն (Armenian)": "hy",
    "Русский (Russian)": "ru",
}

LANG_NAMES = {"en": "English", "hy": "Armenian", "ru": "Russian"}

_STRINGS = {
    # ---- generic / hero ----
    "app_subtitle": {
        "en": "CV-based intelligent interviewing — analysis, adaptive questions, "
              "problem-solving, authenticity checks and a graded verdict.",
        "hy": "Ինքնակենսագրականի վրա հիմնված խելացի հարցազրույց՝ վերլուծություն, "
              "ադապտիվ հարցեր, խնդիրների լուծում, իսկության ստուգում և գնահատված եզրակացություն։",
        "ru": "Умное интервью на основе резюме — анализ, адаптивные вопросы, "
              "решение задач, проверка подлинности и итоговая оценка.",
    },
    # ---- sidebar ----
    "session": {"en": "Session", "hy": "Աշխատաշրջան", "ru": "Сессия"},
    "candidate": {"en": "Candidate", "hy": "Թեկնածու", "ru": "Кандидат"},
    "role": {"en": "Role", "hy": "Դեր", "ru": "Должность"},
    "project": {"en": "Project", "hy": "Նախագիծ", "ru": "Проект"},
    "adaptive_state": {"en": "Adaptive", "hy": "Ադապտիվ", "ru": "Адаптивный"},
    "reset": {"en": "🔄 Reset / Start over", "hy": "🔄 Վերսկսել", "ru": "🔄 Сбросить / Заново"},
    "mode": {"en": "Mode", "hy": "Ռեժիմ", "ru": "Режим"},
    "mode_new": {"en": "New interview", "hy": "Նոր հարցազրույց", "ru": "Новое интервью"},
    "mode_compare": {"en": "Compare candidates", "hy": "Համեմատել թեկնածուներին",
                     "ru": "Сравнить кандидатов"},
    "language": {"en": "Language", "hy": "Լեզու", "ru": "Язык"},
    "auto_read": {"en": "🔊 Read questions aloud",
                  "hy": "🔊 Կարդալ հարցերը բարձրաձայն",
                  "ru": "🔊 Озвучивать вопросы"},
    # ---- step labels ----
    "step_upload": {"en": "1 · Upload", "hy": "1 · Վերբեռնում", "ru": "1 · Загрузка"},
    "step_analysis": {"en": "2 · Analysis", "hy": "2 · Վերլուծություն", "ru": "2 · Анализ"},
    "step_interview": {"en": "3 · Interview", "hy": "3 · Հարցազրույց", "ru": "3 · Интервью"},
    "step_verdict": {"en": "4 · Verdict", "hy": "4 · Եզրակացություն", "ru": "4 · Вердикт"},
    # ---- upload stage ----
    "upload_title": {"en": "📄 Step 1 — Upload CV & set the interview context",
                     "hy": "📄 Քայլ 1 — Վերբեռնեք ինքնակենսագրականը և սահմանեք համատեքստը",
                     "ru": "📄 Шаг 1 — Загрузите резюме и задайте контекст интервью"},
    "job_direction": {"en": "🎯 Job direction *", "hy": "🎯 Աշխատանքի ուղղություն *",
                      "ru": "🎯 Направление вакансии *"},
    "industry": {"en": "🏭 Target industry", "hy": "🏭 Թիրախ ոլորտ", "ru": "🏭 Целевая отрасль"},
    "company_type": {"en": "🏢 Company type", "hy": "🏢 Ընկերության տեսակ", "ru": "🏢 Тип компании"},
    "company": {"en": "⭐ Specific company (optional)", "hy": "⭐ Կոնկրետ ընկերություն (ըստ ցանկության)",
                "ru": "⭐ Конкретная компания (необязательно)"},
    "interview_focus": {"en": "🧭 Interview focus", "hy": "🧭 Հարցազրույցի ֆոկուս",
                        "ru": "🧭 Фокус интервью"},
    "interview_language": {"en": "🗣 Interview language", "hy": "🗣 Հարցազրույցի լեզու",
                           "ru": "🗣 Язык интервью"},
    "num_questions": {"en": "❓ Number of questions", "hy": "❓ Հարցերի քանակ",
                      "ru": "❓ Количество вопросов"},
    "adaptive_cb": {"en": "🔄 Adaptive interview — follow-ups & difficulty that adapt to answers",
                    "hy": "🔄 Ադապտիվ հարցազրույց — հարցերը հարմարվում են պատասխաններին",
                    "ru": "🔄 Адаптивное интервью — вопросы подстраиваются под ответы"},
    "jd_label": {"en": "📋 Paste the job description (optional, improves matching)",
                 "hy": "📋 Տեղադրեք աշխատանքի նկարագրությունը (ըստ ցանկության)",
                 "ru": "📋 Вставьте описание вакансии (необязательно, улучшает подбор)"},
    "extra_context": {"en": "📝 Additional context for the interviewer (optional)",
                      "hy": "📝 Լրացուցիչ համատեքստ հարցազրուցավարի համար (ըստ ցանկության)",
                      "ru": "📝 Дополнительный контекст для интервьюера (необязательно)"},
    "upload_cv": {"en": "📄 Upload your CV (PDF) *", "hy": "📄 Վերբեռնեք ինքնակենսագրականը (PDF) *",
                  "ru": "📄 Загрузите резюме (PDF) *"},
    "upload_project": {"en": "📦 Upload a project to be interviewed on (optional)",
                       "hy": "📦 Վերբեռնեք նախագիծ (ըստ ցանկության)",
                       "ru": "📦 Загрузите проект для вопросов (необязательно)"},
    "analyze_cv": {"en": "🚀 Analyze CV", "hy": "🚀 Վերլուծել", "ru": "🚀 Анализировать"},
    "resume_prev": {"en": "↩️ Resume previous interview",
                    "hy": "↩️ Շարունակել նախորդ հարցազրույցը",
                    "ru": "↩️ Продолжить прошлое интервью"},
    # ---- analysis stage ----
    "analysis_title": {"en": "📊 Step 2 — CV Analysis", "hy": "📊 Քայլ 2 — Վերլուծություն",
                       "ru": "📊 Шаг 2 — Анализ резюме"},
    "target_role": {"en": "🎯 Target role", "hy": "🎯 Թիրախ դեր", "ru": "🎯 Целевая роль"},
    "cv_match": {"en": "CV–Role match", "hy": "Համապատասխանություն", "ru": "Соответствие"},
    "why_match": {"en": "Why this match score", "hy": "Ինչու այս գնահատականը", "ru": "Почему такая оценка"},
    "key_skills": {"en": "🛠 Key skills", "hy": "🛠 Հիմնական հմտություններ", "ru": "🛠 Ключевые навыки"},
    "strengths": {"en": "💪 Strengths", "hy": "💪 Ուժեղ կողմեր", "ru": "💪 Сильные стороны"},
    "gaps": {"en": "⚠️ Gaps", "hy": "⚠️ Բացեր", "ru": "⚠️ Пробелы"},
    "back": {"en": "⬅️ Back", "hy": "⬅️ Հետ", "ru": "⬅️ Назад"},
    "start_interview": {"en": "➡️ Start interview", "hy": "➡️ Սկսել հարցազրույցը", "ru": "➡️ Начать интервью"},
    # ---- interview stage ----
    "interview_title": {"en": "💬 Step 3 — Interview", "hy": "💬 Քայլ 3 — Հարցազրույց",
                        "ru": "💬 Шаг 3 — Интервью"},
    "question_of": {"en": "Question {a} of {b}", "hy": "Հարց {a} / {b}", "ru": "Вопрос {a} из {b}"},
    "read_aloud": {"en": "🔊 Read question aloud", "hy": "🔊 Կարդալ հարցը բարձրաձայն",
                   "ru": "🔊 Озвучить вопрос"},
    "record_voice": {"en": "🎤 Record a voice answer (optional)",
                     "hy": "🎤 Ձայնագրեք պատասխանը (ըստ ցանկության)",
                     "ru": "🎤 Запишите голосовой ответ (необязательно)"},
    "transcribe": {"en": "📝 Transcribe voice → answer", "hy": "📝 Վերծանել ձայնը → պատասխան",
                   "ru": "📝 Расшифровать голос → ответ"},
    "your_answer": {"en": "✍️ Your answer", "hy": "✍️ Ձեր պատասխանը", "ru": "✍️ Ваш ответ"},
    "submit": {"en": "✅ Submit answer", "hy": "✅ Ուղարկել պատասխանը", "ru": "✅ Отправить ответ"},
    "next_question": {"en": "➡️ Next question", "hy": "➡️ Հաջորդ հարցը", "ru": "➡️ Следующий вопрос"},
    "finish": {"en": "🏁 Finish & generate report", "hy": "🏁 Ավարտել և ստեղծել հաշվետվություն",
               "ru": "🏁 Завершить и создать отчёт"},
    "evaluation": {"en": "📋 Evaluation", "hy": "📋 Գնահատում", "ru": "📋 Оценка"},
    "prev_questions": {"en": "📝 Previous questions", "hy": "📝 Նախորդ հարցերը",
                       "ru": "📝 Предыдущие вопросы"},
    "your_answer_h": {"en": "🗣 Your answer", "hy": "🗣 Ձեր պատասխանը", "ru": "🗣 Ваш ответ"},
    # ---- report stage ----
    "report_title": {"en": "📈 Step 4 — Final Verdict & Report",
                     "hy": "📈 Քայլ 4 — Վերջնական եզրակացություն",
                     "ru": "📈 Шаг 4 — Итоговый вердикт и отчёт"},
    "overall": {"en": "Overall score", "hy": "Ընդհանուր գնահատական", "ru": "Общий балл"},
    "grade": {"en": "Grade", "hy": "Գնահատական", "ru": "Оценка"},
    "recommendation": {"en": "Recommendation", "hy": "Առաջարկ", "ru": "Рекомендация"},
    "authenticity": {"en": "Authenticity", "hy": "Իսկություն", "ru": "Подлинность"},
    "download": {"en": "📥 Download report", "hy": "📥 Ներբեռնել հաշվետվությունը",
                 "ru": "📥 Скачать отчёт"},
    "new_interview": {"en": "🔄 Start a new interview", "hy": "🔄 Սկսել նոր հարցազրույց",
                      "ru": "🔄 Начать новое интервью"},
    # ---- compare stage ----
    "compare_title": {"en": "🏆 Compare Candidates", "hy": "🏆 Համեմատել թեկնածուներին",
                      "ru": "🏆 Сравнение кандидатов"},
    "no_saved": {"en": "No saved candidate reports yet. Finish an interview to add one.",
                 "hy": "Դեռ պահպանված հաշվետվություններ չկան։",
                 "ru": "Пока нет сохранённых отчётов. Завершите интервью."},
    "rank": {"en": "Rank", "hy": "Տեղ", "ru": "Место"},
    # ---- persona modes ----
    "persona": {"en": "I am a…", "hy": "Ես…", "ru": "Я…"},
    "persona_candidate": {"en": "🎓 Candidate (practice)",
                          "hy": "🎓 Թեկնածու (պրակտիկա)",
                          "ru": "🎓 Кандидат (практика)"},
    "persona_interviewer": {"en": "🧑‍💼 Interviewer (evaluate)",
                            "hy": "🧑‍💼 Հարցազրուցավար (գնահատում)",
                            "ru": "🧑‍💼 Интервьюер (оценка)"},
    "candidate_hint": {
        "en": "Practice mode: you'll get coaching feedback and tips to improve before the real interview.",
        "hy": "Պրակտիկ ռեժիմ՝ կստանաք խորհուրդներ և բարելավման ուղիներ իրական հարցազրույցից առաջ։",
        "ru": "Режим практики: вы получите советы и рекомендации для подготовки к реальному интервью."},
    "interviewer_hint": {
        "en": "Evaluation mode: focused on objective scoring and a hire/no-hire decision for selection.",
        "hy": "Գնահատման ռեժիմ՝ օբյեկտիվ միավորներ և աշխատանքի ընդունման որոշում։",
        "ru": "Режим оценки: объективные баллы и решение о найме для отбора."},
    # ---- interview description (free text) ----
    "interview_desc": {
        "en": "🗒 Describe the interview in your own words (optional)",
        "hy": "🗒 Նկարագրեք հարցազրույցը ձեր բառերով (ըստ ցանկության)",
        "ru": "🗒 Опишите интервью своими словами (необязательно)"},
    "interview_desc_ph": {
        "en": "e.g. A friendly 30-min screening; my CV is marketing but I'm pivoting to product. "
              "Go easy on deep coding, focus on transferable skills and motivation.",
        "hy": "օր․՝ բարյացակամ 30 րոպեանոց զրույց․ ինքնակենսագրականս մարքեթինգ է, բայց անցնում եմ "
              "product․ խորը կոդից խուսափիր, կենտրոնացիր փոխանցելի հմտությունների վրա։",
        "ru": "напр.: дружелюбный 30-мин скрининг; резюме по маркетингу, перехожу в продакт. "
              "Меньше глубокого кода, упор на переносимые навыки и мотивацию."},
    # ---- skip ----
    "skip": {"en": "⏭ Skip (0 points)", "hy": "⏭ Բաց թողնել (0 միավոր)",
             "ru": "⏭ Пропустить (0 баллов)"},
    "skipped": {"en": "Skipped — scored 0.", "hy": "Բաց թողնված — 0 միավոր։",
                "ru": "Пропущено — 0 баллов."},
    "weaknesses": {"en": "⚠️ Weaknesses", "hy": "⚠️ Թույլ կողմեր", "ru": "⚠️ Слабые стороны"},
    "improve": {"en": "🚀 How to improve", "hy": "🚀 Ինչպես բարելավել", "ru": "🚀 Как улучшить"},
    "questions_label": {"en": "Questions", "hy": "Հարցեր", "ru": "Вопросы"},
    "show_best": {"en": "💡 Show the best possible answer",
                  "hy": "💡 Ցույց տալ լավագույն հնարավոր պատասխանը",
                  "ru": "💡 Показать лучший возможный ответ"},
    "best_answer": {"en": "🌟 Best possible answer", "hy": "🌟 Լավագույն պատասխանը",
                    "ru": "🌟 Лучший возможный ответ"},
    "ai_detection": {"en": "AI-answer detection", "hy": "AI-պատասխանի հայտնաբերում",
                     "ru": "Обнаружение AI-ответа"},
}


def current_lang():
    return st.session_state.get("ui_lang", "en")


def t(key, **fmt):
    """Translate a UI key into the current language, with optional .format()."""
    entry = _STRINGS.get(key)
    code = current_lang()
    if not entry:
        text = key
    else:
        text = entry.get(code) or entry.get("en") or key
    if fmt:
        try:
            text = text.format(**fmt)
        except Exception:
            pass
    return text
