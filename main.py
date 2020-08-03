import gspread
SPREADSHEET_KEY = "1CFCmrvcCiBng64ltEQ0usIxGyDIcLMwG3Tak67ugOrk"

SUBJECT = "נושא"
SUBJECT2 = f"{SUBJECT} 2"
SUBJECT3 = f"{SUBJECT} 3"
SUBJECTS = [SUBJECT, SUBJECT2, SUBJECT3]
TYPE = "סוג"
QUESTION_BODY = "שאלה"

gc = gspread.service_account("credentials.json")
file = gc.open_by_key(SPREADSHEET_KEY)

types = file.worksheet("types").col_values(1)
topics = file.worksheet("topics").col_values(1)
queries = file.worksheet("query").get_all_records()

questions = file.worksheet("questions").get_all_records()
for q in questions:
    q["topics"] = {topic for topic in [q[SUBJECT], q[SUBJECT2], q[SUBJECT3]] if topic}
    if not q["topics"]:
        print(f"ERROR: NO TOPIC for {q[QUESTION_BODY]}")
        exit(1)
    for key in SUBJECTS:
        del q[key]

# todo clear old results
query_sheet = file.worksheet("query")

found_questions = set()
for i in range(len(queries)):
    query = queries[i]
    if not query[SUBJECT]:
        continue
    query_result = []
    for question in questions:
        if question[QUESTION_BODY] in found_questions:
            continue

        if query[SUBJECT] in question["topics"] and \
                (not query[TYPE]  # query doesn't specify type
                 or query[TYPE] == question[TYPE]):
            query_result.append(question[QUESTION_BODY])
            found_questions.add(question[QUESTION_BODY])

    for j in range(len(query_result)):
        query_sheet.update_cell(2 + i, 3 + j, query_result[j])
