#!groovy

// http://javadoc.jenkins-ci.org/

if(args.length != 2) {
    println("incorrect parameter amount");
    return;
}

def itemName = args[0];
def command = args[1];

if(command != "start" && command != "stop") {
    println("command not understood: " + command);
    return;
}

def jenkinsInstance = jenkins.model.Jenkins.getInstance();

def project = jenkinsInstance.getItem(itemName);
def jobs = project.getAllJobs();
def dummyList = new ArrayList();
for(job in jobs) {
    if(command == "start") {
        println(job.name + " started");
        // even though the documentation says that actions can be null you
        // get an npe if it is
        jenkinsInstance.queue.schedule2(job, 0, dummyList);
    } else if(command == "stop") {
        for(build in job.getBuilds()) {
            if(build.isBuilding()) {
                if(build.getExecutor() != null) {
                    println("stopping " + build);
                    build.getExecutor().doStop();
                } else {
                    println(build + " has null executor");
                }
            }
        }
    }
}
