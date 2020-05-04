Jenkins job handler
-------------------

This is a modified version of this jenkins job deleter: https://gitlab.dbc.dk/ai/jenkins-build-deleter
At the moment it can stop jenkins jobs.

```
$ job-stopper --help
usage: job-stopper [-h] [--base-url BASE_URL] [-u USER] [--keep-latest-build]
                   folders [folders ...]

positional arguments:
  folders               Jenkins folders to search for builds to delete

optional arguments:
  -h, --help            show this help message and exit
  --base-url BASE_URL   Url for jenkins instance
  -u USER, --user USER  jenkins username and password, separated by a :
  --keep-latest-build   Keep the newest running build
```

### Usage
`job-stopper -u username:password job/conversion-flows2`
