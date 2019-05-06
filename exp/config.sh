# RUBBoS configuration parameters.

# Cloud
# FILL IN CLOUD NAMES: "emulab" or "cloudlab".
#     EXAMPLE: readonly WEB_CLOUD_NAME="cloudlab"
readonly WEB_CLOUD_NAME=""
readonly APP_CLOUD_NAME=""
readonly MIDDL_CLOUD_NAME=""
readonly DB_CLOUD_NAME=""
readonly CLIENT_CLOUD_NAME=""
readonly BENCH_CLOUD_NAME=""

# WCE mode
WEB_HARDWARE_WCEMODE="disable"
readonly WEB_SDPARM_VERSION="1.10"
APP_HARDWARE_WCEMODE="disable"
readonly APP_SDPARM_VERSION="1.10"
MIDDL_HARDWARE_WCEMODE="disable"
readonly MIDDL_SDPARM_VERSION="1.10"
DB_HARDWARE_WCEMODE="disable"
readonly DB_SDPARM_VERSION="1.10"

# Hardware
# FILL IN HARDWARE TYPES: "pc3000", if in Emulab. "c8220", if in CloudLab.
#     EXAMPLE: readonly WEB_HARDWARE_TYPE="c8220"
readonly WEB_HARDWARE_TYPE=""
readonly APP_HARDWARE_TYPE=""
readonly MIDDL_HARDWARE_TYPE=""
readonly DB_HARDWARE_TYPE=""
readonly CLIENT_HARDWARE_TYPE=""

# Network
# FILL IN NODES: "node[1-6].[EXPERIMENT_NAME].infosphere.emulab.net", if in Emulab.
#                "clnode___.clemson.cloudlab.us", if in CloudLab.
#     EXAMPLE: readonly WEB_NET_NODES="node1.tutorial.infosphere.emulab.net", if you named your
#              Emulab cloud "tutorial".
#     EXAMPLE: readonly WEB_NET_NODES="clnode085.clemson.cloudlab.us", if node 085 was allocated
#              for you on CloudLab (check on tab "List View" on your experiment's page).
# FILL IN USERNAMES: Username of the account you created.
#     EXAMPLE: readonly WEB_NET_USERNAME="burdell"
readonly WEB_NET_NODES=""
readonly WEB_NET_USERNAME=""
readonly APP_NET_NODES=""
readonly APP_NET_USERNAME=""
readonly MIDDL_NET_NODE=""
readonly MIDDL_NET_USERNAME=""
readonly DB_NET_NODES=""
readonly DB_NET_USERNAME=""
readonly CLIENT_NET_NODES=""
readonly CLIENT_NET_USERNAME=""
readonly BENCH_NET_NODE=""
readonly BENCH_NET_USERNAME=""

# Benchmark configuration
# FILL IN WORKLOAD: A value between 500 and 1000 (number of concurrent clients).
#     EXAMPLE: readonly BENCH_WORKLOAD="750"
readonly BENCH_TYPE="read-write"
readonly BENCH_WORKLOAD=""
readonly BENCH_UPRAMPTIMEINMS="180000"
readonly BENCH_SESSIONRUNTIMEINMS="180000"
readonly BENCH_DOWNRAMPTIMEINMS="60000"

# Java configuration
readonly APP_JAVA_VERSION="1.6.0"
readonly APP_JAVA_MAXHEAPSIZEINMB="2000"
readonly MIDDL_JAVA_VERSION="1.6.0"
readonly MIDDL_JAVA_MAXHEAPSIZEINMB="2000"
readonly CLIENT_JAVA_VERSION="1.6.0"

# Apache HTTP server configuration
# Reference: http://httpd.apache.org/docs/2.2/mod/core.html
# Reference: http://httpd.apache.org/docs/2.2/mod/mpm_common.html
readonly WEB_HTTPD_VERSION="2.2.22"
readonly WEB_HTTPD_TIMEOUT="5"
readonly WEB_HTTPD_KEEPALIVE="off"
readonly WEB_HTTPD_MAXKEEPALIVEREQUESTS="-"
readonly WEB_HTTPD_KEEPALIVETIMEOUT="-"
readonly WEB_HTTPD_MULTIPROCESSINGMODE="worker"
readonly WEB_HTTPD_SERVERLIMIT="200"
readonly WEB_HTTPD_THREADLIMIT="300"
readonly WEB_HTTPD_STARTSERVERS="1"
readonly WEB_HTTPD_MAXCLIENTS="300"
readonly WEB_HTTPD_MINSPARETHREADS="5"
readonly WEB_HTTPD_MAXSPARETHREADS="50"
readonly WEB_HTTPD_THREADSPERCHILD="150"
readonly WEB_HTTPD_MAXREQUESTSPERCHILD="0"
readonly WEB_HTTPD_LOGRESPONSETIME="on"

# mod_jk configuration
readonly WEB_MODJK_VERSION="1.2.32"

# Tomcat configuration
# Reference: https://tomcat.apache.org/tomcat-5.5-doc/config/http.html
readonly APP_LOG4J_VERSION="1.2.17"
readonly APP_TOMCAT_VERSION="5.5.17"
readonly APP_TOMCAT_MAXTHREADS="330"
readonly APP_TOMCAT_MINSPARETHREADS="5"
readonly APP_TOMCAT_MAXSPARETHREADS="50"
readonly APP_TOMCAT_ACCEPTCOUNT="6000"
readonly APP_TOMCAT_LOGRESPONSETIME="on"

# C-JDBC configuration
# Reference: http://c-jdbc.ow2.org/current/doc/userGuide/html/userGuide.html
readonly MIDDL_JDBC_VERSION="5.1.7"
readonly MIDDL_CJDBC_VERSION="2.0.2"
readonly MIDDL_CJDBC_CONNINITPOOLSIZE="30"
readonly MIDDL_CJDBC_CONNMINPOOLSIZE="25"
readonly MIDDL_CJDBC_CONNMAXPOOLSIZE="90"
readonly MIDDL_CJDBC_CONNIDLETIMEOUT="30"
readonly MIDDL_CJDBC_CONNWAITTIMEOUT="10"
readonly MIDDL_CJDBC_LOGRESPONSETIME="on"

# MySQL configuration
readonly DB_LIBAIO_VERSION="0.3.111"
readonly DB_MYSQL_VERSION="5.6.40"
readonly DB_MYSQL_MAXCONNECTIONS="500"

# Collectl
readonly WEB_COLLECTL_VERSION="4.0.4"
readonly APP_COLLECTL_VERSION="4.0.4"
readonly MIDDL_COLLECTL_VERSION="4.0.4"
readonly DB_COLLECTL_VERSION="4.0.4"
