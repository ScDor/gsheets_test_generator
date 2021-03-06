from dataclasses import dataclass
from datetime import datetime
import gspread
import logging
from config import *
from utils import *
from email.utils import parseaddr
from hebrew_phrases import *
import random

UNKNOWN_USER_NAME = "?"
MISSING_TOPIC = "MISSING_TOPIC"
MAX_QUESTIONS = 5

OUTPUT_URL_COL = 4
OUTPUT_NAME_COL = 5
OUTPUT_RUNTIME_COL = 6
OUTPUT_METADATA_COLUMNS = [OUTPUT_URL_COL, OUTPUT_NAME_COL, OUTPUT_RUNTIME_COL]

OUTPUT_SUBJECT_ROW = 1
OUTPUT_TYPE_ROW = 2
OUTPUT_BAGRUT_ROW = 3


@dataclass
class QuestionHandler:
    def __init__(self, sheet):
        questions = sheet.get_all_records()
        random.shuffle(questions)
        for q in questions:
            q["topics"] = {topic for topic in [q[SUBJECT], q[SUBJECT2], q[SUBJECT3]]
                           if topic}
            if not q["topics"]:
                # logging.warning(f"no topic for question {q[QUESTION_BODY][:80]}") # todo use
                q["topics"] = MISSING_TOPIC

            for key in SUBJECTS:
                del q[key]

            q[BAGRUT] = True if q[BAGRUT] else False

        self.questions = questions
        logging.info(f"read {len(self.questions)} questions")


class QueryHandler:
    def __init__(self, ui_sheet, gc, question_handler):
        self.ui_sheet = ui_sheet
        self.question_handler = question_handler

        if self.ui_sheet.cell(1, 4).value == BUILDING_TEST:  # todo cleaner code
            self.ui_sheet.update_cell(1, OUTPUT_NAME_COL, UNKNOWN_USER_NAME)

        self.email = self.ui_sheet.cell(1, OUTPUT_NAME_COL).value
        if "@" not in parseaddr(self.email)[1]:
            self.ui_sheet.update_cell(1, OUTPUT_NAME_COL, MSG_INVALID_EMAIL)
            raise ValueError("Invalid email")

        self.ui_sheet.update_cell(1, OUTPUT_NAME_COL, BUILDING_TEST)

        queries = create_query_dictionary(self.ui_sheet)

        self.run_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.output_file = copy_sheet_into(gc, OUTPUT_TEMPLATE_KEY,
                                           title=f"{self.run_time}_{self.email}",
                                           folder_id=OUTPUT_FOLDER_ID)
        try:
            gc.insert_permission(self.output_file.id, self.email, perm_type="user",
                                 role="writer", notify="True", email_message=MSG_EMAIL_BODY)
        except gspread.exceptions.APIError:
            logging.error(f"invalid email {self.email}")
            raise ValueError(f"Invalid email {self.email}")

        self.output_sheet = self.output_file.sheet1

        print(self.run_time, self.email, self.output_file.url)
        self.log_run()

        self.found_questions = set()
        self.process_queries(queries)

        self.clear_query()
        self.clear_old_results()

    def process_queries(self, queries):
        for query_index in range(len(queries)):  # todo prettify
            q = queries[query_index]
            if not q[SUBJECT]:
                continue
            matching_questions = self.find_matching_questions(q)

            self.output_sheet.update_cell(OUTPUT_SUBJECT_ROW, 2 + query_index, q[SUBJECT])
            self.output_sheet.update_cell(OUTPUT_TYPE_ROW, 2 + query_index, q[TYPE])
            self.output_sheet.update_cell(OUTPUT_BAGRUT_ROW, 2 + query_index, q[BAGRUT])

            if not matching_questions:
                self.output_sheet.update_cell(3, 3 + query_index, MSG_NO_QUESTIONS_FOUND)
                continue

            for col in range(min(MAX_QUESTIONS, len(matching_questions))):
                self.output_sheet.update_cell(4 + col, 2 + query_index,
                                              matching_questions[col])

    def find_matching_questions(self, query):
        result = []
        for question in self.question_handler.questions:
            body = question[QUESTION_BODY]
            if body in self.found_questions:
                continue

            if query[SUBJECT] in question["topics"] and \
                    ((not query[TYPE]) or query[TYPE] == question[TYPE]):

                if (query[BAGRUT] == YES and not question[BAGRUT]) \
                        or (query[BAGRUT] == NO and question[BAGRUT]):
                    continue
                result.append(body)
                self.found_questions.add(body)
        return result

    def log_run(self):
        next_vacant_row = len(self.ui_sheet.col_values(OUTPUT_NAME_COL)) + 1

        self.ui_sheet.update_cell(next_vacant_row, OUTPUT_URL_COL, self.output_file.url)
        self.ui_sheet.update_cell(next_vacant_row, OUTPUT_NAME_COL,
                                  censor_email(self.email))
        self.ui_sheet.update_cell(next_vacant_row, OUTPUT_RUNTIME_COL, self.run_time)

        self.ui_sheet.update_cell(1, OUTPUT_NAME_COL, "")  # removes name

    def clear_query(self):
        logging.info("clearing user input")
        for i in range(3, 22 + 1):  # todo improve by batch_update rather than one by one
            for j in range(1, 3 + 1):
                self.ui_sheet.update_cell(i, j, "")
        logging.info("done clearing input")

    def clear_old_results(self):
        logging.info("clearing old results")
        result_count = len(self.ui_sheet.col_values(OUTPUT_URL_COL)) - 2
        if result_count > 10:
            for i in range(result_count):
                for j in [OUTPUT_NAME_COL, OUTPUT_RUNTIME_COL, OUTPUT_URL_COL]:
                    self.ui_sheet.update_cell(3 + i, j, "")
        logging.info("done clearing old results")


def create_query_dictionary(sheet):
    keys = sheet.row_values(2)[:3]
    queries = [q[:3] for q in sheet.get_all_values()[2:]]  # third row onwards
    return [dict(zip(keys, v)) for v in queries]


def main():
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

    question_handler = QuestionHandler(question_sheet)
    query = QueryHandler(query_sheet, gc, question_handler)


if __name__ == '__main__':
    main()
