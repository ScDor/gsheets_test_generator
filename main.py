from dataclasses import dataclass
from datetime import datetime
import gspread
import logging
from config import *
from hebrew_phrases import *

UNKNOWN_USER_NAME = "?"

MISSING_TOPIC = "FOO"

MAX_QUESTIONS = 5
UNKNOWN_USER = "?"
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s\t%(message)s', datefmt='%Y-%m-%d %H:%M:%S')

gc = gspread.service_account("credentials.json")
logging.info("google login successful")

logging.debug("reading files")
question_file = gc.open_by_key(QUESTION_SPREADSHEET_KEY)
ui_file = gc.open_by_key(UI_SPREADSHEET_KEY)

logging.debug("reading question types and topics")
types = question_file.worksheet("types").col_values(1)
topics = question_file.worksheet("topics").col_values(1)

question_sheet = question_file.worksheet("questions")
query_sheet = ui_file.worksheet("query")


@dataclass
class QuestionHandler:
    def __init__(self, sheet):
        questions = sheet.get_all_records()
        for q in questions:
            q["topics"] = {topic for topic in [q[SUBJECT], q[SUBJECT2], q[SUBJECT3]]
                           if topic}
            if not q["topics"]:
                logging.warning(f"no topic for question {q[QUESTION_BODY][:80]}")
                q["topics"] = MISSING_TOPIC

            for key in SUBJECTS:
                del q[key]
        self.questions = questions
        logging.info(f"read {len(self.questions)} questions")


question_handler = QuestionHandler(question_sheet)


def create_query_dictionary(sheet):
    keys = sheet.row_values(2)[:2]
    queries = [q[:2] for q in sheet.get_all_values()[2:]]  # third row onwards
    return [dict(zip(keys, v)) for v in queries]


@dataclass
class QueryHandler:

    def __init__(self, ui_sheet):
        output_name_column = 4

        if ui_sheet.cell(1, 4).value == BUILDING_TEST:
            ui_sheet.update_cell(1, output_name_column, UNKNOWN_USER_NAME)
        self.current_user = ui_sheet.cell(1, output_name_column).value
        ui_sheet.update_cell(1, output_name_column, BUILDING_TEST)

        queries = create_query_dictionary(ui_sheet)

        self.run_time = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        self.output_file = gc.create(f"{self.run_time}_{self.current_user}", OUTPUT_FOLDER_ID)
        self.output_sheet = self.output_file.sheet1
        print(self.output_file.url)  # todo remove
        self.log_run()

        self.found_questions = set()
        self.process_queries(queries)

    def process_queries(self, queries):
        for i in range(len(queries)):  # todo prettify
            q = queries[i]
            if not q[SUBJECT]:
                continue
            matching_questions = self.find_matching_questions(q)

            self.output_sheet.update_cell(1, 1 + i, q[SUBJECT])
            self.output_sheet.update_cell(2, 1 + i, q[TYPE])

            if not matching_questions:
                self.output_sheet.update_cell(3, 1 + i, NO_QUESTIONS_FOUND)
                continue

            for j in range(min(len(matching_questions), MAX_QUESTIONS)):
                self.output_sheet.update_cell(3 + j, 1 + i, matching_questions[j])

    def find_matching_questions(self, q):
        result = []
        for question in question_handler.questions:
            body = question[QUESTION_BODY]
            if body in self.found_questions:
                continue

            if q[SUBJECT] in question["topics"] and (not q[TYPE]  # q doesn't specify type
                                                     or q[TYPE] == question[TYPE]):
                result.append(body)
                self.found_questions.add(body)
        return result

    def log_run(self):
        output_url_column = 3
        output_name_column = 4
        output_time_column = 5

        next_vacant_row = len(query_sheet.col_values(output_name_column)) + 1

        query_sheet.update_cell(next_vacant_row, output_name_column, self.current_user)
        query_sheet.update_cell(next_vacant_row, output_time_column, self.run_time)
        query_sheet.update_cell(next_vacant_row, output_url_column, self.output_file.url)

        query_sheet.update_cell(1, output_name_column, "")  # removes name



query = QueryHandler(query_sheet)
