#!/usr/bin/env python3
from itertools import chain, islice, takewhile
import os
import re
import requests
from time import sleep, time
from string import Template

# Store the value of you cookies in 'cookies.txt'
COOKIES = open('cookies.txt', 'r').read().strip().replace('cookie: ', '', 1)
# Change output dir if you like
LEETCODE_DIR = '../leetcode-solutions-py'
# Change how many days to look back
DAYS_TO_IMPORT=365*100
SUBMISSIONS_URL = 'https://leetcode.com/api/submissions/?offset={}&limit={}'
PROBLEM_URL = 'https://leetcode.com/problems/{}/'
GRAPHQL_URL = 'https://leetcode.com/graphql'
THROTTLE_SECONDS = 1
EXTENSIONS = {
    "cpp": 'cpp',
    "java": 'java',
    "python": 'py',
    "python3": 'py',
    "mysql": 'sql',
    "mssql": 'sql',
    "oraclesql": 'sql',
    "c": 'c',
    "csharp": 'cs',
    "javascript": 'js',
    "ruby": 'rb',
    "bash": 'sh',
    "swift": 'swift',
    "golang": 'go',
    "scala": 'scala',
    "html": 'html',
    "pythonml": 'py',
    "kotlin": 'kt',
    "rust": 'rs',
    "php": 'php'
}
SLUG_RE = re.compile(r"[^-0-9a-z ]", re.IGNORECASE)
DESCRIPTION_TEMPLATE = Template("""
${difficulty}: #${questionId} ${title}
=======================
[View on LeetCode](${problem_url})
</hr>
${content}
""")

IMPORT_SINCE = int(time()) - (DAYS_TO_IMPORT * 24 * 60 * 60)

def question_data(slug):
    return {
        "operationName": "questionData",
        "variables": {
            "titleSlug": slug
        },
        "query": """query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionId
                questionFrontendId
                boundTopicId
                title
                titleSlug
                content
                difficulty
                sampleTestCase
            }
        }"""
    }


def get_submissions(batch_size=20):
    """Gets all submissions in `batch_size` chunks"""
    offset = 1351
    while True:
        print(f"getting batch #{offset + 1}")
        response = requests.get(
            SUBMISSIONS_URL.format(offset, batch_size), 
            headers={'Cookie': COOKIES})
        try:
            json_response = response.json()
        except requests.exceptions.JSONDecodeError:
            offset += 1
            continue
        if 'detail' in json_response:
            print(json_response['detail'])
        if 'submissions_dump' in json_response:
            yield json_response['submissions_dump']
        if not 'has_next' in json_response or not json_response['has_next']:
            break
        offset += 1
        sleep(THROTTLE_SECONDS)


def add_description(submission):
    title = submission['title']
    slug = title_to_slug(title)
    print(f'{slug}: getting description')
    response = requests.post(
        GRAPHQL_URL, 
        json=question_data(slug),
        headers={'Cookie': COOKIES})
    try:
        json_response = response.json()
    except requests.exceptions.JSONDecodeError:
        print("VIGOSS>>>")
        json_response = None
    problem_url = PROBLEM_URL.format(slug)
    if json_response is None or json_response['data'] is None or json_response['data']['question'] is None or json_response['data']['question']['questionFrontendId'] is None:
        slug = "99999" + "-" + slug
        return {**submission, 'err': 'VIGOSS', 'slug': slug, 'problem_url': problem_url} 
    slug = json_response['data']['question']['questionFrontendId'].zfill(4) + "-" + slug
    return {**submission, **json_response['data']['question'], 'slug': slug, 'problem_url': problem_url}


def is_accepted(submission):
    return 'status_display' in submission and submission['status_display'] == 'Accepted'

def is_recent(submission):
    return 'timestamp' in submission and submission['timestamp'] >= IMPORT_SINCE


def title_to_slug(title):
    return SLUG_RE.sub("", title).replace(" ", "-").lower()


def store_solution(solution):
    slug = solution['slug']
    print(f'{slug}: storing')
    solution_dir = f'{LEETCODE_DIR}/{slug}/'
    if not os.path.exists(solution_dir):
        os.makedirs(solution_dir)

        description_file = open(solution_dir+'README.md', 'w')
        description_file.write(DESCRIPTION_TEMPLATE.substitute(solution))
        description_file.close

        test_file = open(solution_dir+'input.txt', 'w')
        test_file.write(solution['sampleTestCase'])
        test_file.close
    else:
        print(f'{slug}: folder exists')

    filename = f'{solution_dir}solution_{solution["id"]}.{EXTENSIONS[solution["lang"]]}'
    if not os.path.exists(filename):
        print(f'{slug}: writing solution #{solution["id"]}')
        solution_file = open(filename, 'w')
        solution_file.write(solution['code'])
        solution_file.close
    else:
        print(f'{slug}: solution #{solution["id"]} already exists')


submissions = chain.from_iterable(get_submissions())
recent_submissions = takewhile(is_recent, submissions)
accepted_submissions = filter(is_accepted, recent_submissions)
accepted_submissions_details = map(add_description, accepted_submissions)
for solution in accepted_submissions_details:
    if not solution['slug'].startswith("99999"):   
        store_solution(solution)
