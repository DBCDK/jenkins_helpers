#!/usr/bin/python3

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import urllib.request
import xml.etree.ElementTree as ET

class ProcessError(Exception):
    pass

class JenkinsAPI(object):
    def __init__(self, base_url, folder, user, api_key):
        self.base_url = base_url
        self.auth = make_auth(user, api_key)
        self.folder_url, self.branch_jobs = self.get_jenkins_folder(folder)

    def make_request(self, url, data=None, method=None):
        headers = {
            "Authorization": self.auth
        }
        if data is not None:
            headers["Content-Type"] = "text/xml"
        req = urllib.request.Request(url, data, headers)
        if method is not None:
            req.get_method = lambda: method
        return urllib.request.urlopen(req)

    def check_job_exists(self, job_name):
        try:
            self.make_request("{}/job/{}/config.xml".format(self.folder_url,
                job_name))
            return True
        except urllib.error.URLError:
            return False

    def create_jenkins_item(self, name, config_path):
        url_safe_name = make_url_safe_name(name)
        url = "{}/createItem?name={}".format(self.folder_url, url_safe_name)
        if not self.check_job_exists(url_safe_name):
            config = read_config(name, config_path)
            p = self.make_request(url, config)
            print("job for branch {} created".format(name))
        else:
            print("job for branch {} already exists".format(name))

    def delete_jenkins_item(self, name, branch_job_url):
        try:
            self.make_request("{}/doDelete".format(branch_job_url),
                method="POST")
            print("job for branch {} deleted".format(name))
        except urllib.error.URLError as e:
            print("could not delete job {}: {}".format(name, str(e)))

    def get_branch_jobs(self, folder):
        try:
            js_response = self.make_request(
                "{}/api/json?tree=jobs[name,jobs[url]]"
                .format(self.base_url))
            js = json.loads(js_response.read().decode("utf8"))
            for job in js["jobs"]:
                if job["_class"] == "com.cloudbees.hudson.plugins.folder.Folder"\
                        and job["name"] == folder:
                    return [j["url"] for j in job["jobs"]]
        except urllib.error.URLError as e:
            print("couldn't find branch jobs: {}".format(str(e)),
                file=sys.stderr)

    def get_jenkins_folder(self, folder):
        url = "{}/api/xml?tree=jobs[url,name,jobs[fullName,url]]"\
            "&xpath=hudson/job/name[text()='{}']/parent::*".format(
            self.base_url, folder)
        folder_xml = self.make_request(url)
        root = ET.parse(folder_xml)
        folder_url = root.findtext("url")
        branches = [j.findtext("url") for j in root.findall("job")]
        return (folder_url, branches)

    def get_branch_from_config(self, job_url):
        config = self.make_request("{}/config.xml".format(job_url))
        if config is not None:
            root = ET.parse(config)
            return root.findtext("scm/branches/"
                "hudson.plugins.git.BranchSpec/name")

    def find_deleted_branches(self, folder, remote_branches):
        branch_jobs = self.get_branch_jobs(folder)
        branches = set([self.get_branch_from_config(b) for b in branch_jobs])
        return branches - set(remote_branches)

class GitHandler(object):
    def __init__(self, repo_url):
        self.repo_url = repo_url
        self.tmp_dir = tempfile.mkdtemp()
        self.remote_name = "origin"

    def init_repo(self):
        call_process(["git", "init", "--bare", self.tmp_dir])
        os.chdir(self.tmp_dir)
        call_process(["git", "remote", "add", self.remote_name,
            self.repo_url])
        call_process(["git", "fetch", "--depth", "1"])

    def get_branches(self):
        try:
            self.init_repo()
            branches = subprocess.check_output(["git", "branch", "-r",
                "--list"])
            branches = branches.decode("utf8").split()
            branches = [b.lstrip(self.remote_name).strip("/") for b in branches]
            return branches
        except (UnicodeDecodeError, ProcessError) as e:
            print("error getting branches for repo {}: {}".format(
                self.repo_url, str(e)), file=sys.stderr)
            traceback.print_exc()
        finally:
            shutil.rmtree(self.tmp_dir)

def call_process(args, **kwargs):
    try:
        subprocess.check_call(args, **kwargs)
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise ProcessError("error calling {}".format(str(args))) from e

def make_url_safe_name(name):
    return re.sub("[/\s]", "__", name)

def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", help="git feature branch to build")
    parser.add_argument("folder", help="jenkins folder")
    parser.add_argument("-u", "--user", help="jenkins user")
    parser.add_argument("--api-key")
    parser.add_argument("--config", help="xml config to base job on")
    parser.add_argument("-s", "--server")
    args = parser.parse_args()
    return args

def read_config(branch_name, config_path):
    fp = open(config_path, "rb")
    b = fp.read()
    return b.replace("{BRANCH_NAME}".encode("utf8"),
        branch_name.encode("utf8"))

def make_auth(user, password):
    encoded_user_info = base64.b64encode("{}:{}".format(user, password)
        .encode("utf8"))
    return "Basic {}".format(encoded_user_info.decode("utf8"))

def main():
    args = setup_args()
    jenkins_api = JenkinsAPI(args.server, args.folder, args.user,
        args.api_key)
    jenkins_api.create_jenkins_item(args.branch, args.config)

if __name__ == "__main__":
    main()
