#!/usr/bin/env python3

import argparse
import collections
import os

import requests

types = {
    "folder": "Folder",
    "view": "ListView",
    "multi_branch_project": "WorkflowMultiBranchProject",
    "workflow_job": "WorkflowJob",
}
folder_types = ("folder", "view", "multi_branch_project")

class JobTypeException(Exception):
    pass

Folder = collections.namedtuple("Folder", ["name", "url", "jobs"])
Job = collections.namedtuple("Job", ["name", "url", "builds"])
Build = collections.namedtuple("Build", ["url", "number", "success"])
Error = collections.namedtuple("Error", ["status_code", "text", "causing_url"])

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("folders", nargs="+",
        help="Jenkins folders to search for builds to delete")
    parser.add_argument("--base-url", default="https://is.dbc.dk",
        help="Url for jenkins instance")
    parser.add_argument("-u", "--user", help="jenkins username and password, separated by a :")
    parser.add_argument("--keep-latest-build", action="store_true",
        help="Keep the newest running build")
    return parser.parse_args()

class JobHandler(object):
    def __init__(self, user):
        self.session = requests.session()
        username, password = user.split(":")
        self.session.auth = (username, password)
        self.errors = []

    def get_job_type(self, job_spec):
        for k, v in types.items():
            if v in job_spec["_class"]:
                return k
        return job_spec["_class"]

    def get_jobs(self, folder_url):
        response = self.session.get(f"{folder_url}/api/json")
        response.raise_for_status()
        folder_spec = response.json()
        # If the program is started with a job url and not a folder url make a dummy folder
        if self.get_job_type(folder_spec) == "workflow_job":
            folder = Folder("", "", [{"url": folder_url}])
        elif self.get_job_type(folder_spec) not in folder_types:
            raise JobTypeException(f"Invalid folder type: {folder_spec['_class']}")
        else:
            folder = Folder(folder_spec["name"], folder_spec["url"],
                folder_spec["jobs"])
        for j in folder.jobs:
            job_response = self.session.get(f"{j['url']}/api/json?depth=2&tree=name,url,builds[url,number,building]")
            job_response.raise_for_status()
            job_spec = job_response.json()
            job_type = self.get_job_type(job_spec)
            if job_type not in folder_types:
                yield Job(job_spec["name"], job_spec["url"], job_spec["builds"])
            else:
                yield from self.get_jobs(j["url"])

    def get_builds(self, job):
        return [b["url"] for b in sorted(job.builds,
            key=lambda x: int(x["number"])) if b["building"]]

    def stop_jobs(self, builds):
        for url in builds:
            print(f"Stopping {url}")
            self.session.post(f"{url}/stop")

def main():
    args = setup_args()
    user = args.user
    if user is None:
        user = f"{os.environ['JENKINS_USERNAME']}:{os.environ['JENKINS_PASSWORD']}"
    handler = JobHandler(user)
    for folder in args.folders:
        print(f"Looking through {args.base_url}/{folder}")
        for job in handler.get_jobs(f"{args.base_url}/{folder}"):
            builds = handler.get_builds(job)
            if args.keep_latest_build:
                builds = builds[1:]
            handler.stop_jobs(builds)
    if handler.errors:
        for error in handler.errors:
            print(f"Error: {error}")
