#!/usr/bin/python -E
'''
provides an installer for ovirt-engine-reports
TODO:
1. move all prints to constants (either stored locally or in another package
3. check for DB before execution DB creation (execute select 1 from db and check rc)
4. add additional messages printed in the end of install
5.
'''
import logging
import os
import sys
import traceback
import getpass
import shutil
import cracklib
import types
import tempfile
import re
import glob
import argparse

import common_utils as utils

from decorators import transactionDisplay
import pwd


DIR_DEPLOY = "/usr/share/ovirt-engine"
JRS_APP_NAME = "ovirt-engine-reports"
JRS_DB_NAME = "ovirtenginereports"
JRS_PACKAGE_NAME = "jasperreports-server"
DIR_WAR="%s/%s.war" % (DIR_DEPLOY, JRS_APP_NAME)
FILE_JS_SMTP="%s/WEB-INF/js.quartz.properties" % DIR_WAR
FILE_APPLICATION_SECURITY_WEB="%s/WEB-INF/applicationContext-security-web.xml" % DIR_WAR
FILE_JRS_DATASOURCES="%s/WEB-INF/js-jboss7-ds.xml" % DIR_WAR
JRS_INSTALL_SCRIPT="js-install-ce.sh"

db_dict = None
ENGINE_DB_DATABASE = "engine"
ENGINE_HISTORY_DB_NAME = "ovirt_engine_history"
REPORTS_DB_USER = 'engine_reports'
DWH_USER = 'engine_history'

REPORTS_SERVER_DIR = "/usr/share/%s"  % JRS_PACKAGE_NAME
REPORTS_SERVER_BUILDOMATIC_DIR = "%s/buildomatic" % REPORTS_SERVER_DIR
FILE_JASPER_DB_CONN = "%s/default_master.properties" % REPORTS_SERVER_BUILDOMATIC_DIR
FILE_DATABASE_CONFIG = "/etc/ovirt-engine/engine.conf.d/10-setup-database.conf"
FILE_DATABASE_DWH_CONFIG = "/etc/ovirt-engine-dwh/engine-dwh.conf.d/10-setup-database-dwh.conf"
FILE_DATABASE_REPORTS_CONFIG = "/etc/ovirt-engine-reports/engine-reports.conf.d/10-setup-database-reports.conf"
FILE_ENGINE_CONF_DEFAULTS = "/usr/share/ovirt-engine/services/ovirt-engine/ovirt-engine.conf"
FILE_ENGINE_CONF = "/etc/ovirt-engine/engine.conf"

REPORTS_PACKAGE_DIR = "/usr/share/ovirt-engine-reports"
SSL2JKSTRUST = "%s/ssl2jkstrust.py" % REPORTS_PACKAGE_DIR
FILE_DB_DATA_SOURCE = "%s/reports/resources/reports_resources/JDBC/data_sources/ovirt.xml" % REPORTS_PACKAGE_DIR
DIR_REPORTS_CUSTOMIZATION="%s/server-customizations" % REPORTS_PACKAGE_DIR
DIR_OVIRT_THEME="%s/reports/resources/themes/ovirt-002dreports-002dtheme" % REPORTS_PACKAGE_DIR

REPORTS_JARS_DIR = "/usr/share/java/ovirt-engine-reports"

FILE_DEPLOY_VERSION = "/etc/ovirt-engine/jrs-deployment.version"
DIR_PKI = "/etc/pki/ovirt-engine"
OVIRT_REPORTS_ETC="/etc/ovirt-engine/ovirt-engine-reports"
OVIRT_REPORTS_TRUST_STORE="%s/trust.jks" % OVIRT_REPORTS_ETC
OVIRT_REPORTS_TRUST_STORE_PASS="mypass"

DB_EXIST = False
MUCK_PASSWORD="oVirtadmin2009!"
PGDUMP_EXEC = "/usr/bin/pg_dump"
FILE_TMP_SQL_DUMP = tempfile.mkstemp(suffix=".sql", dir="/tmp")[1]
DIR_TMP_WAR = tempfile.mkdtemp(dir="/tmp")

#Error Messages
MSG_ERROR_BACKUP_DB = "Error: Database backup failed"
MSG_ERROR_RESTORE_DB = "Error: Database restore failed"
MSG_ERROR_DB_EXISTS = "ERROR: Found the database for ovirt-engine-reports, but could not find the WAR directory!\n\
In order to remedy this situation, please drop the ovirt-engine-reports database by executing:\n\
/usr/bin/dropdb -U %s -h %s -p %s %s"

DIR_TEMP_SCHEDULE=tempfile.mkdtemp()

log_file = None

def _verifyUserPermissions():
    username = pwd.getpwuid(os.getuid())[0]
    if os.geteuid() != 0:
        sys.exit(
            'Error: insufficient permissions for user {user}, '
            'you must run with user root.'.format(
                user=username
            )
        )


@transactionDisplay("Deploying Server")
def deployJs(db_dict, TEMP_PGPASS):
    '''
    execute js-ant with various directives
    '''
    global DB_EXIST
    try:
        logging.debug("Deploying Server ant scripts")
        current_dir = os.getcwd()
        os.chdir(REPORTS_SERVER_BUILDOMATIC_DIR)
        DB_EXISTED = False

        tempSmtpFile = tempfile.mktemp(dir="/tmp")
        # Copy the SMTP configuration aside before we deploy the Jasper war
        smtpConfFile = FILE_JS_SMTP
        if os.path.exists(smtpConfFile):
            shutil.copy2(smtpConfFile, tempSmtpFile)

        # If we need to refresh the war, we also need to drop the DB
        if DB_EXIST:
            logging.debug("Removing DB")
            utils.clearDB(db_dict, TEMP_PGPASS)
            DB_EXIST = False
            DB_EXISTED = True

        if isWarInstalled():
            shutil.rmtree(DIR_WAR)

        logging.debug("Linking Postgresql JDBC driver to %s/conf_source/db/postgresql/jdbc for installation" % REPORTS_SERVER_BUILDOMATIC_DIR)
        shutil.copyfile("/usr/share/java/postgresql-jdbc.jar", "%s/conf_source/db/postgresql/jdbc/postgresql-jdbc.jar" % REPORTS_SERVER_BUILDOMATIC_DIR)

        # create DB if it didn't exist:
        if not DB_EXISTED:
            logging.debug('Creating DB')
            utils.createDB(db_dict)
            utils.createLang(db_dict, TEMP_PGPASS)
        logging.debug("Installing Jasper")
        for cmd in (
            'init-js-db-ce',
            'import-minimal-ce',
            'deploy-webapp-ce',
        ):
            cmdList = [
                './js-ant',
                cmd
            ]
            output, rc = utils.execCmd(
                cmdList=cmdList,
                failOnError=True,
                msg='Failed step {command} of JasperReports Server'.format(
                    command=cmd
                )
            )

        # FIXME: this is a temp WA for an issue in JS: running js-install always
        # returns 0
        if "BUILD FAILED" in output:
            raise Exception("Failed installation of JasperReports Server")

        logging.debug("Removing deployment of Postgresql JDBC driver and unused dodeploy file post installation")
        for obsolete_file in (
            "%s/postgresql-jdbc.jar" % DIR_DEPLOY,
            "%s/WEB-INF/lib/postgresql-jdbc.jar" % DIR_WAR,
            "%s/%s.war.dodeploy" % (DIR_DEPLOY,JRS_APP_NAME),
        ):
            if os.path.exists(obsolete_file):
                os.remove(obsolete_file)

        # Restore the smtp configuration file
        if os.path.exists(tempSmtpFile):
            shutil.copy2(tempSmtpFile, smtpConfFile)
        if DB_EXISTED:
            logging.debug("setting DB_EXIST to True since it was previously set")
            DB_EXIST = True
    except:
        raise
    finally:
        os.chdir(current_dir)
        if os.path.exists(tempSmtpFile):
            os.remove(tempSmtpFile)

def setDeploymentDetails(db_dict):
    '''
    set the password for the user postgres
    '''
    logging.debug("Setting DB pass")

    logging.debug("editing jasper db connectivity file")
    file_handler = utils.TextConfigFileHandler(FILE_JASPER_DB_CONN)
    file_handler.open()
    # TODO: when JS support for passwords with $$ is added, remove 'replace'
    file_handler.editParam("dbPassword", db_dict["password"].replace("$", "$$"))
    file_handler.editParam("dbUsername", db_dict["username"])
    file_handler.editParam("dbHost", db_dict["host"])
    file_handler.editParam("dbPort", db_dict["port"])
    file_handler.editParam("js.dbName", db_dict['dbname'])
    file_handler.editParam("webAppNameCE", JRS_APP_NAME)
    file_handler.editParam("appServerDir", DIR_DEPLOY)
    file_handler.close()

def setReportsDatasource(db_dict):
    logging.debug("editing reports datasource file %s", FILE_DB_DATA_SOURCE)
    xml_editor = utils.XMLConfigFileHandler(FILE_DB_DATA_SOURCE)
    xml_editor.open()
    xml_editor.editParams({'/jdbcDataSource/connectionUrl':"jdbc:postgresql://%s:%s/%s" % (db_dict["host"],db_dict["port"],ENGINE_HISTORY_DB_NAME)})
    xml_editor.editParams({'/jdbcDataSource/connectionUser':db_dict["dwh_user"]})
    xml_editor.editParams({'/jdbcDataSource/connectionPassword':db_dict["dwh_pass"]})
    xml_editor.close()

def resetReportsDatasourcePassword():
    logging.debug("editing reports datasource file %s", FILE_DB_DATA_SOURCE)
    xml_editor = utils.XMLConfigFileHandler(FILE_DB_DATA_SOURCE)
    xml_editor.open()
    xml_editor.editParams({'/jdbcDataSource/connectionPassword':""})
    xml_editor.close()

@transactionDisplay("Updating Redirect Servlet")
def updateServletDbRecord(TEMP_PGPASS):
    '''
    update the RedirectServletReportsPage record in vdc_options
    '''

    # This is done due to jboss's bug: https://issues.jboss.org/browse/JBAS-9345
    # Since we cannot rely on jboss to redirect to a secure port, we insert
    # the Full url into the db.

    protocol, fqdn, port = getHostParams()
    hostUrl = "%s://%s:%s/%s" % (protocol, fqdn, port, JRS_APP_NAME)
    query = (
        "update vdc_options "
        "set option_value='{hostUrl}' "
        "where option_name='RedirectServletReportsPage';"
    ).format(
        hostUrl=hostUrl
    )
    cmd = [
        "/usr/bin/psql",
        "-w",
        "-U", db_dict['engine_user'],
        "-h", db_dict['host'],
        "-p", db_dict['port'],
        "-d", db_dict['engine_db'],
        "-c", query,
    ]
    utils.execCmd(
        cmdList=cmd,
        failOnError=True,
        msg="Failed updating main page redirect",
        envDict={'ENGINE_PGPASS': TEMP_PGPASS},
    )

@transactionDisplay("Setting DB connectivity")
def setDBConn():
    shutil.copyfile("%s/default_master.properties" % REPORTS_PACKAGE_DIR, FILE_JASPER_DB_CONN)
    if db_dict['password']:
        setDeploymentDetails(db_dict)
    else:
        raise OSError("Cannot find password for db")

def getDbDictFromOptions():
    if os.path.exists(FILE_DATABASE_CONFIG):
        handler = utils.TextConfigFileHandler(FILE_DATABASE_CONFIG)
        handler.open()
        dhandler = handler
        if os.path.exists(FILE_DATABASE_REPORTS_CONFIG):
            dhandler = utils.TextConfigFileHandler(FILE_DATABASE_REPORTS_CONFIG)
            dhandler.open()
        db_dict = {
            'dbname': (
                dhandler.getParam('REPORTS_DATABASE') or
                JRS_DB_NAME
            ),
            'host': handler.getParam('ENGINE_DB_HOST').strip('"'),
            'port': handler.getParam('ENGINE_DB_PORT').strip('"'),
            'username': (
                dhandler.getParam('REPORTS_USER') or
                REPORTS_DB_USER
            ),
            'password': (
                dhandler.getParam('REPORTS_PASSWORD') or
                utils.generatePassword()
            ),
            'engine_db': (
                handler.getParam('ENGINE_DB_DATABASE').strip('"') or
                ENGINE_DB_DATABASE
            ),
            'engine_user': handler.getParam('ENGINE_DB_USER').strip('"'),
            'engine_pass': handler.getParam('ENGINE_DB_PASSWORD').strip('"'),
        }
        handler.close()
        dhandler.close()
    else:
        db_dict = {
            'dbname': JRS_DB_NAME,
            'host': utils.getDbHostName(),
            'port': utils.getDbPort(),
            'username': utils.getDbAdminUser(),
            'password': utils.getPassFromFile(utils.getDbAdminUser()),
            'engine_db': ENGINE_DB_DATABASE,
            'engine_user': utils.getDbAdminUser(),
            'engine_pass': utils.getPassFromFile(utils.getDbAdminUser()),
        }

    if os.path.exists(FILE_DATABASE_DWH_CONFIG):
        dwhandler = utils.TextConfigFileHandler(FILE_DATABASE_DWH_CONFIG)
        dwhandler.open()
        db_dict['dwh_database'] = dwhandler.getParam('DWH_DATABASE')
        db_dict['dwh_user'] = dwhandler.getParam('DWH_USER')
        db_dict['dwh_pass'] = dwhandler.getParam('DWH_PASSWORD')
    else:
        db_dict['dwh_database'] = 'ovirt_engine_history'
        db_dict['dwh_user'] = utils.getDbAdminUser()
        db_dict['dwh_pass'] = utils.getPassFromFile(utils.getDbAdminUser())

    return db_dict

def getDBStatus(db_dict, TEMP_PGPASS):
    exists = owned = False
    for dbdict in (
        db_dict,
        {
            'dbname': JRS_DB_NAME,
            'host': db_dict['host'],
            'port': db_dict['port'],
            'username': db_dict['engine_user'],
            'password': db_dict['engine_pass'],
            'engine_user': db_dict['engine_user'],
            'engine_pass': db_dict['engine_pass'],
        },
        {
            'dbname': JRS_DB_NAME,
            'host': db_dict['host'],
            'port': db_dict['port'],
            'username': 'admin',
            'password': 'dummy',
            'engine_user': db_dict['engine_user'],
            'engine_pass': db_dict['engine_pass'],
        },
    ):
        exists, owned = utils.dbExists(dbdict, TEMP_PGPASS)
        if exists:
            break

    return exists, owned

def getDbCredentials(
    hostdefault='',
    portdefault='',
    userdefault='',
):
    """
    get db params from user
    """
    dbhost = utils.askQuestion(
        question='Enter the host name for the DB server',
        default=hostdefault,
    )

    dbport = utils.askQuestion(
        question='Enter the port of the remote DB server',
        default=portdefault or '5432',
    )

    dbuser = utils.askQuestion(
        question='Provide a remote DB user',
        default=userdefault,
    )

    userInput = getPassFromUser(
        'Please choose a password for the db user: '
    )
    # We do not need verification for the re-entered password
    userInput2 = getpass.getpass("Re-type password: ")
    if userInput != userInput2:
            print "ERROR: passwords don't match"
            return getDbCredentials(dbhost, dbport, dbuser)

    return dbhost, dbport, dbuser, userInput

def getAdminPass():
    userInput = getPassFromUser(
        'Please choose a password for the reports admin user(s) '
        '(ovirt-admin): '
    )
    # We do not need verification for the re-entered password
    userInput2 = getPassFromUser(
        'Retype password: '
    )
    if userInput != userInput2:
            print "ERROR: passwords don't match"
            return getDbCredentials()

    return userInput


def getPassFromUser(string):
    """
    get a single password from the user
    """
    userInput = getpass.getpass(string)
    if type(userInput) != types.StringType or len(userInput) == 0:
        print "Cannot accept an empty password"
        return getPassFromUser(string)

    try:
        cracklib.FascistCheck(userInput)
    except:
        print "Warning: Weak Password."

    return userInput

def editOvirtEngineAdminXml(password):
    """
    edit ovirt-engine-admin xml file and set password
    TODO handle superuser password.
    """
    logging.debug("setting password for ovirt-engine-admin")
    xmlFile  = "%s/reports/users/ovirt-002dadmin.xml" % REPORTS_PACKAGE_DIR
    logging.debug("opening xml file")
    xmlObj = utils.XMLConfigFileHandler(xmlFile)
    xmlObj.open()
    logging.debug("setting password")
    node = utils.getXmlNode(xmlObj, "/user/password")
    node.setContent(password)
    logging.debug("closing file")
    xmlObj.close()

@transactionDisplay("Customizing Server")
def customizeJs():
    customizeJsImple()
    deployCustomization()

def deployCustomization():
    """
    copy customizations directory into war file
    """
    # We have 2 options, either implement a file/directory walker
    # or use cp. i chose cp.
    logging.debug("Copying customizations files into place")
    cmd = "cp -rpf %s/* %s" % (DIR_REPORTS_CUSTOMIZATION, DIR_WAR)
    (rc, output) = utils.execExternalCmd(cmd, True, "Error while trying to copy customizations files into place")

def customizeJsImple():
    """
    link all jars from /usr/share/java/ovirt-engine-reports to reports war lib folder
    """

    # Link all jar files into WAR directory
    logging.debug("linking jar files")
    destDir = "%s/WEB-INF/lib" % DIR_WAR
    destJars = os.listdir(destDir)
    for destJar in destJars:
        jarPath = "%s/%s" % (destDir,destJar)
        if os.path.islink(jarPath):
            if not os.path.exists(os.readlink(jarPath)):
                logging.debug("removing current file link %s, since it is broken", destJar)
                os.unlink(jarPath)
    sourceDir = REPORTS_JARS_DIR
    jarFiles = os.listdir(sourceDir)
    for jarFile in jarFiles:
        logging.debug("linking %s" % jarFile)
        target = "%s/%s" % (sourceDir, jarFile)
        link = "%s/%s" % (destDir, jarFile)
        logging.debug("Linking %s to %s" % (target, link))
        shutil.copyfile(target, link)
    #temp fix for JRS logging
    for filename in ('slf4j-api.jar', 'slf4j-log4j12.jar'):
        for srcDir in (
            '/usr/share/java/slf4j',
            '/usr/share/jbos-as/modules/org/slf4j/main',
        ):
            sourceFile = os.path.join(
                srcDir,
                filename
            )
            destFile = os.path.join(
                destDir,
                filename
            )
            if (
                os.path.exists(sourceFile) and
                not os.path.exists(destFile)
            ):
                shutil.copyfile(sourceFile, destFile)
                break

def isWarUpdated():
    """
    check the war version and compare it with current rpm version
    """
    warUpdated = False
    if os.path.exists(FILE_DEPLOY_VERSION):
        logging.debug("%s exists, checking version" % FILE_DEPLOY_VERSION)

        fd = file(FILE_DEPLOY_VERSION, 'r')
        deployedVersion = fd.readline()
        deployedVersion = deployedVersion.strip()
        found = re.search("(\d+\.\d+)\.(\d+\-.+)", deployedVersion)
        if not found:
            logging.error("%s is not a valid version string" % deployedVersion)
            raise Exception("Cannot parse version string, please report this error")

        rpmVersion = utils.getAppVersion(JRS_PACKAGE_NAME)

        if deployedVersion != rpmVersion:
            logging.debug("%s differs from %s, war deployment required" % (deployedVersion, rpmVersion))
        else:
            logging.debug("war directory is up to date with installed version")
            warUpdated = True
    else:
        logging.debug("%s does not exist, assuming clean install" % FILE_DEPLOY_VERSION)
        fd = open(FILE_DEPLOY_VERSION, "w")
        fd.write(utils.getAppVersion(JRS_PACKAGE_NAME))
        fd.close()
        logging.debug("Created JRS version file")

    return warUpdated

@transactionDisplay("Exporting scheduled reports")
def exportScheduale():
    """
    export scheduale reports to a temp direcotry
    """
    logging.debug("exporting scheduale reports")
    current_dir = os.getcwd()

    try:
        os.chdir(REPORTS_SERVER_BUILDOMATIC_DIR)

        # Export scheduale reports to a temp directory
        cmd = [
            './js-export.sh',
            '--output-dir',
            DIR_TEMP_SCHEDULE,
            '--report-jobs',
            '/',
        ]
        utils.execCmd(
            cmdList=cmd,
            failOnError=True,
            msg="Failed while exporting scheduale reports",
        )

    except:
        logging.error("Exception caught, passing it along to main loop")
        raise

    finally:
        os.chdir(current_dir)

@transactionDisplay("Importing scheduled reports")
def importScheduale(inputDir=DIR_TEMP_SCHEDULE):
    """
    import scheduale reports
    """
    logging.debug("importing scheduale reports")
    current_dir = os.getcwd()
    try:
        os.chdir(REPORTS_SERVER_BUILDOMATIC_DIR)

        # Import current scheduale reports
        cmd = "./js-import.sh --input-dir %s --update" % inputDir
        utils.execExternalCmd(cmd, True, "Failed while importing scheduale reports")

    except:
        logging.error("Exception caught, passing it along to main loop")
        raise

    finally:
        os.chdir(current_dir)

@transactionDisplay("Backing up reports DB")
def backupDB(db_dict, TEMP_PGPASS):
    # pg_dump -C -E UTF8  --column-inserts --disable-dollar-quoting  --disable-triggers -U postgres --format=p -f $dir/$file  ovirt-engine
    logging.debug("DB Backup started")
    cmd = [
        PGDUMP_EXEC,
        "-C",
        "-E",
        "UTF8",
        "-w",
        "--column-inserts",
        "--disable-dollar-quoting",
        "--disable-triggers",
        "--format=p",
        "-U", db_dict["username"],
        "-h", db_dict["host"],
        "-p", db_dict["port"],
        "-f", FILE_TMP_SQL_DUMP,
        db_dict['dbname'],
    ]
    output, rc = utils.execCmd(
        cmdList=cmd,
        failOnError=True,
        msg=MSG_ERROR_BACKUP_DB,
        envDict={'ENGINE_PGPASS': TEMP_PGPASS},
    )
    logging.debug("DB Backup completed successfully")
    logging.debug("DB Saved to %s", FILE_TMP_SQL_DUMP)

@transactionDisplay("Restoring reports DB")
def restoreDB(db_dict, TEMP_PGPASS):
    #psql -U postgres -f <backup directory>/<backup_file>
    if os.path.exists(FILE_TMP_SQL_DUMP):
        logging.debug("DB Restore started")
        # Drop
        utils.clearDB(db_dict, TEMP_PGPASS)
        # Restore
        cmd = [
            "/usr/bin/psql",
            "-w",
            "-U", db_dict["username"],
            "-h", db_dict["host"],
            "-p", db_dict["port"],
            "-f", FILE_TMP_SQL_DUMP,
        ]

        output, rc = utils.execCmd(
            cmdList=cmd,
            failOnError=True,
            msg=MSG_ERROR_RESTORE_DB,
            envDict={'ENGINE_PGPASS': TEMP_PGPASS},
        )
        logging.debug("DB Restore completed successfully")
        os.remove(FILE_TMP_SQL_DUMP)
    else:
        logging.debug("No SQL Dump file found, No DB Restore needed")

@transactionDisplay("Backing up Installation")
def backupWAR():
    logging.debug("backing up WAR directory")
    sourceDir = DIR_WAR
    shutil.rmtree(DIR_TMP_WAR)
    shutil.copytree(sourceDir, DIR_TMP_WAR, symlinks=True)
    logging.debug("WAR backup ed to %s", DIR_TMP_WAR)

@transactionDisplay("Restoring Installation")
def restoreWAR():
    if os.path.exists(DIR_TMP_WAR):
        logging.debug("restoring WAR direcotry")
        destDir = DIR_WAR

        if os.path.exists(destDir):
            logging.debug("Removing dir %s", destDir)
            shutil.rmtree(destDir)

        logging.debug("copying %s over %s", DIR_TMP_WAR, destDir)
        shutil.copytree(DIR_TMP_WAR, destDir, symlinks=True)
        customizeJsImple()
    else:
        logging.debug("no saved WAR dir found, will not restore WAR")

def isOvirtEngineInstalled():
    keystore = os.path.join(DIR_PKI, "keys", "engine.p12")
    engine_ear = "%s/engine.ear" % DIR_DEPLOY

    if os.path.exists(keystore):
        logging.debug("%s exists, ovirt-engine is installed", keystore)
        return True
    elif os.path.exists(engine_ear):
        logging.debug("ear exists, ovirt-engine is installed")
        return True
    else:
        return False

def getHostParams(secure=True):
    """
    get protocol, hostname & secured port from /etc/ovirt-engine/engine.conf
    """

    protocol = "https" if secure else "http"
    hostFqdn = None
    port = None

    if not os.path.exists(FILE_ENGINE_CONF_DEFAULTS):
        raise Exception("Could not find %s" % FILE_ENGINE_CONF_DEFAULTS)
    engineConfigFiles = [
        FILE_ENGINE_CONF_DEFAULTS,
        FILE_ENGINE_CONF,
    ]
    engineConfigDir = FILE_ENGINE_CONF + ".d"
    if os.path.isdir(engineConfigDir):
        additionalEngineConfigFiles = glob.glob(engineConfigDir + "/*.conf")
        additionalEngineConfigFiles.sort()
        engineConfigFiles.extend(additionalEngineConfigFiles)

    config = dict(
        ENGINE_PROXY_ENABLED=None,
        ENGINE_PROXY_HTTPS_PORT=None,
        ENGINE_PROXY_HTTP_PORT=None,
        ENGINE_HTTPS_ENABLED=None,
        ENGINE_HTTPS_PORT=None,
        ENGINE_HTTP_PORT=None,
        ENGINE_FQDN=None,
    )
    for f in engineConfigFiles:
        logging.debug("reading %s", f)
        file_handler = utils.TextConfigFileHandler(f)
        file_handler.open()

        for k in config.keys():
            v = file_handler.getParam(k)
            if v is not None:
                config[k] = v

        file_handler.close()

    proxyEnabled = config["ENGINE_PROXY_ENABLED"]
    if (
        proxyEnabled is not None and
        proxyEnabled.lower() in ["true", "t", "yes", "y", "1"]
    ):
        if secure:
            port = config["ENGINE_PROXY_HTTPS_PORT"]
        else:
            port = config["ENGINE_PROXY_HTTP_PORT"]
    elif config["ENGINE_HTTPS_ENABLED"]:
        if secure:
            port = config["ENGINE_HTTPS_PORT"]
        else:
            port = config["ENGINE_HTTP_PORT"]

    hostFqdn = config["ENGINE_FQDN"]
    if port and secure:
        logging.debug("Secure web port is: %s", port)
    elif port and not secure:
        logging.debug("Web port is: %s", port)
    if hostFqdn:
        logging.debug("Host's FQDN: %s", hostFqdn)

    if not hostFqdn:
        logging.error("Could not find the HOST FQDN from %s", engineConfigFiles)
        raise Exception("Cannot find host fqdn from configuration, please verify that ovirt-engine is configured")
    if not port:
        logging.error("Could not find the web port from %s", engineConfigFiles)
        raise Exception("Cannot find the web port from configuration, please verify that ovirt-engine is configured")

    return (protocol, hostFqdn, port)

def isWarInstalled():
    """
    checks if the ovirt-engine-reports.war directory exists, return True if it is
    False otherwise
    """
    jasperreports = DIR_WAR
    if os.path.exists(jasperreports):
	logging.debug('Found WAR folder %s', jasperreports)
        return True
    else:
        return False

@transactionDisplay("Editing XML files")
def editXmlFiles():
    logging.debug("Editing xml files for jasper installation")
    for file in ["setup.xml", "app-server.xml"]:
        logging.debug("reading %s" % file)
        fd = open("%s/bin/%s" % (REPORTS_SERVER_BUILDOMATIC_DIR, file), "r")
        file_content = fd.read()
        fd.close()
        logging.debug("replace install path to correct one")
        file_content = file_content.replace("/${jboss7.profile}/deployments", "")
        logging.debug("writing replaced content to %s" % file)
        fd = open("%s/bin/%s" % (REPORTS_SERVER_BUILDOMATIC_DIR, file), "w")
        fd.write(file_content)
        logging.debug("closing file")
        fd.close()

def updateDsJdbc():
    """
        Updating datasource to point to jdbc module.
    """
    file_content = ''
    logging.debug("editing datasources file")
    with open(FILE_JRS_DATASOURCES, "r") as fd:
        file_content = fd.read()
    logging.debug("replace driver to module name")
    file_content = file_content.replace("<driver>postgresql-jdbc.jar</driver>", "<driver>postgresql</driver>")
    logging.debug("writing replaced content to %s" % FILE_JRS_DATASOURCES)
    with open(FILE_JRS_DATASOURCES, "w") as fd:
        fd.write(file_content)
    logging.debug("adding driver section")

    xml_editor = utils.XMLConfigFileHandler(FILE_JRS_DATASOURCES)
    xml_editor.open()
    nodeExists = xml_editor.xpathEval("/datasources/drivers")
    if not nodeExists:
        newDriver = '''
        <drivers>
            <driver name="postgresql" module="org.postgresql">
                <xa-datasource-class>org.postgresql.xa.PGXADataSource</xa-datasource-class>
            </driver>
        </drivers>
        '''
        xml_editor.addNodes("/datasources", newDriver)
    logging.debug("closing file")
    xml_editor.close()

def updateApplicationSecurity():
    """
        Setting the SSO solution
    """
    file_content = ''
    protocol, fqdn, port = getHostParams()
    logging.debug("downloading certificates %s://%s:%s" % (protocol, fqdn, port))
    if protocol == 'https':
        utils.execCmd(
            cmdList=(
                SSL2JKSTRUST,
                '--host=%s' % fqdn,
                '--port=%s' % port,
                '--keystore=%s' % OVIRT_REPORTS_TRUST_STORE,
                '--storepass=%s' % OVIRT_REPORTS_TRUST_STORE_PASS,
            ),
            failOnError=True,
        )
    logging.debug("editing applicationContext-security-web file")
    protocol, fqdn, port = getHostParams()
    hostValidateSessionUrl = (
        '{proto}://{fqdn}:{port}/OvirtEngineWeb/ValidateSession'
    ).format(
        proto=protocol,
        fqdn=fqdn,
        port=port,
    )
    with open(FILE_APPLICATION_SECURITY_WEB, "r") as fd:
        file_content = fd.read()

    logging.debug("replace servlet URL")
    file_content = file_content.replace("http://localhost/OvirtEngineWeb/ValidateSession", hostValidateSessionUrl)

    logging.debug("replace trust store path and pass")
    file_content = file_content.replace(
        "name=\"trustStorePath\" value=\"/usr/local/jboss-as/truststore\"",
        "name=\"trustStorePath\" value=\"%s\"" % OVIRT_REPORTS_TRUST_STORE
    )
    file_content = file_content.replace(
        "name=\"trustStorePassword\" value=\"NoSoup4U\"",
        "name=\"trustStorePassword\" value=\"%s\"" % OVIRT_REPORTS_TRUST_STORE_PASS
    )
    logging.debug("writing replaced content to %s" % FILE_APPLICATION_SECURITY_WEB)
    with open(FILE_APPLICATION_SECURITY_WEB, "w") as fd:
        fd.write(file_content)

@transactionDisplay("Running post setup steps")
def configureRepository(password):
    """
        Run post setup steps - disable unused users, set theme, change superuser password if needed
    """
    savedRepoDir = utils.exportReportsRepository()
    anonymousUserFile = "%s/users/anonymousUser.xml" % savedRepoDir
    jasperAdminFile = "%s/users/jasperadmin.xml" % savedRepoDir
    logging.debug("disabling unused users, if needed")
    if not DB_EXIST and os.path.exists(anonymousUserFile):
        fd = open(anonymousUserFile, "r")
        file_content = fd.read()
        fd.close()
        logging.debug("disabling anonymousUser")
        file_content = file_content.replace("<enabled>true</enabled>", "<enabled>false</enabled>")
        logging.debug("writing replaced content to anonymousUser.xml")
        fd = open(anonymousUserFile, "w")
        fd.write(file_content)
        fd.close()
    if not DB_EXIST and os.path.exists(jasperAdminFile):
        fd = open(jasperAdminFile, "r")
        file_content = fd.read()
        fd.close()
        logging.debug("disabling jasperadmin")
        file_content = file_content.replace("<enabled>true</enabled>", "<enabled>false</enabled>")
        logging.debug("writing replaced content to jasperadmin.xml")
        fd = open(jasperAdminFile, "w")
        fd.write(file_content)
        fd.close()
    logging.debug("changing the theme")
    fd = open("%s/organizations/organizations.xml" % savedRepoDir, "r")
    file_content = fd.read()
    fd.close()
    file_content = file_content.replace("<theme>default</theme>", "<theme>ovirt-reports-theme</theme>")
    logging.debug("writing replaced content to organizations.xml")
    fd = open("%s/organizations/organizations.xml" % savedRepoDir, "w")
    fd.write(file_content)
    fd.close()
    logging.debug("importing back reports")
    current_dir = os.getcwd()
    os.chdir(REPORTS_SERVER_BUILDOMATIC_DIR)
    cmd = "./js-import.sh --input-dir %s --update" % savedRepoDir
    utils.execExternalCmd(cmd, True, "Failed while importing back reports")
    os.chdir(current_dir)
    shutil.rmtree(savedRepoDir)

def main():
    '''
    main
    '''
    global db_dict
    global DB_EXIST
    rc = 0
    preserveReportsJobs = False
    pghba_updated = False

    parser = argparse.ArgumentParser(description='Installs or upgrades your oVirt Engine Reports')
    # Catch when calling ovirt-engine-dwh-setup --help
    args = parser.parse_args()

    try:
        logging.debug("starting main()")
        print "Welcome to ovirt-engine-reports setup utility"

        # Check that oVirt-Engine is installed, otherwise exit gracefully with an informative message
        if not isOvirtEngineInstalled():
            logging.debug("ovirt-engine is not installed, cannot continue")
            print "Please install & configure oVirt engine by executing \"engine-setup\" prior to setting up the oVirt engine reports."
            return 0

        # Check if ovirt-engine is up, if so prompt the user to stop it.
        if utils.stopEngine():
            warUpdated = isWarUpdated()

            if not warUpdated and isWarInstalled():
                logging.debug("war will be updated and was previously deployed, will preserve reports' jobs")
                preserveReportsJobs = True

            if warUpdated and isWarInstalled():
                logging.debug("war is installed and updated. reports will only be refreshed.")

            db_dict = getDbDictFromOptions()
            TEMP_PGPASS = utils.createTempPgpass(
                db_dict=db_dict,
                mode='own',
            )
            dblocal = utils.localHost(db_dict['host'])
            if dblocal:
                pghba_updated = utils.setPgHbaIdent()

            if not utils.dbExists(
                db_dict={
                    'host': db_dict['host'],
                    'port': db_dict['port'],
                    'dbname': db_dict['dwh_database'],
                    'username': db_dict['dwh_user'],
                    'password': db_dict['dwh_pass'],
                    'engine_user': db_dict['engine_user'],
                },
                TEMP_PGPASS=TEMP_PGPASS,
            )[0]:
                raise RuntimeError(
                    'DWH has not been setup, please install ovirt-engine-dwh package '
                    'and execute: \"ovirt-engine-dwh-setup\" before setting up the '
                    'reports.'
                )

            DB_EXIST, owned = getDBStatus(db_dict, TEMP_PGPASS)
            if dblocal:
                if DB_EXIST and not owned:
                    logging.debug(
                        (
                            'Local database {database} found, '
                            'not owned by reports user. Updating '
                            'the owner to {reports_user}'
                        ).format(
                            database=db_dict['dbname'],
                            reports_user=REPORTS_DB_USER,
                        )
                    )
                    utils.updateDbOwner(
                        db_dict=db_dict,
                        origowner=db_dict['username'],
                        newowner=REPORTS_DB_USER,
                    )
            elif not DB_EXIST:
                logging.debug(
                    (
                        'Remote database {database} found, '
                        'not owned by reports user'
                    ).format(
                        database=db_dict['dbname']
                    )
                )
                print 'Remote database found.'
                if utils.askYesNo(
                    'Setup could not connect to remote database server with '
                    'automatically detected credentials. '
                    'Would you like to manually provide db credentials?'
                ):
                    DB_EXIST = False
                    print (
                        'Remote installation selected. Make sure that DBA '
                        'creates a user and the database in the following '
                        ' fashion:\n'
                        '\tcreate role <role> with login '
                        'encrypted password <password>;\n'
                        '\tcreate database ovirtenginereports '
                        'template template0 encoding '
                        '\'UTF8\' lc_collate \'en_US.UTF-8\' '
                        'lc_ctype \'en_US.UTF-8\' '
                        'owner <role>;\n'
                    )
                    while not DB_EXIST:
                        (
                            db_dict['host'],
                            db_dict['port'],
                            db_dict['username'],
                            db_dict['password']
                        ) = getDbCredentials()
                        if os.path.exists(TEMP_PGPASS):
                            os.remove(TEMP_PGPASS)

                        TEMP_PGPASS = utils.createTempPgpass(
                            db_dict=db_dict,
                            mode='own',
                        )
                        DB_EXIST, owned = getDBStatus(
                            db_dict,
                            TEMP_PGPASS,
                        )
                        if not DB_EXIST:
                            print (
                                'error: cannot connect to the '
                                'remote db with provided credentials. '
                                'verify that the provided user is defined '
                                'user exists on a remote db server and '
                                'is the owner of the provided database.\n'
                            )
                else:
                    raise RuntimeError('Could not connect to the remote DB')

            if not isWarInstalled() and DB_EXIST and dblocal:
                logging.error("WAR Directory does not exist but the DB is up and running.")
                raise Exception(MSG_ERROR_DB_EXISTS % (db_dict["username"],
                                                       db_dict["host"],
                                                       db_dict["port"],
                                                       db_dict['dbname']))

            # Edit setup.xml & app-server.xml to remove profile name
            if not warUpdated or not isWarInstalled():
                editXmlFiles()

            logging.debug("Username is %s" % db_dict["username"])
            # Set db connectivity (user/pass)
            if not warUpdated or not isWarInstalled():
                setDBConn()

            # Update reports datasource configuration
            setReportsDatasource(db_dict)

            if not warUpdated and DB_EXIST:
                #backupWAR()
                #backupDB(db_dict, TEMP_PGPASS)
		pass

            # Catch failures on configuration
            try:
                # Export reports if we had a previous installation
                adminPass = None
                savedDir = None
                if preserveReportsJobs:
                    exportScheduale()

                if DB_EXIST and (
                    warUpdated or isWarInstalled()
                ):
                    savedDir = utils.exportUsers()
                else:
                    adminPass = getAdminPass()

                # Execute js-ant to create DB and deploy WAR
                # May also set DB_EXIST to False if WAR is in need of an upgrade
                if not warUpdated or not isWarInstalled():
                    deployJs(db_dict, TEMP_PGPASS)

                logging.debug("Database status: %s" % DB_EXIST)
                # Update oVirt-Engine vdc_options with reports relative url
                updateServletDbRecord(TEMP_PGPASS)

                # If the userPassword var has been populated it means we need to edit the Admin xml file
                if adminPass is not None:
                    editOvirtEngineAdminXml(adminPass)

                if (
                    DB_EXIST and
                    savedDir is not None and
                    (
                        warUpdated or isWarInstalled()
                    )
                ):
                    logging.debug("Importing users")
                    utils.importUsers(savedDir)


                # Execute js-import to add reports to DB
                utils.importReports()

                # We import users twice because we need permissions to be
                # preserved as well as users passwords reset after importing
                # reports in previous step.
                if (
                    DB_EXIST and
                    savedDir is not None and
                    (
                        warUpdated or isWarInstalled()
                    )
                ):
                    logging.debug("Imporing users")
                    utils.importUsers(savedDir)

                # If this is a fresh install, we muck the password in the users xml files
                editOvirtEngineAdminXml(MUCK_PASSWORD)

                # Link all files in ovirt-engine-reports/reports*/jar to /var/lib/jbosas/server/ovirt-engine-slimmed/deploy/ovirt-engine-reports/WEB-INF/lib
                customizeJs()

                # Import scheduale reports if they were previously existing
                if preserveReportsJobs:
                    scheduleDir = DIR_TEMP_SCHEDULE
                    importScheduale(scheduleDir)

                # Edit Data Sources Driver Info
                updateDsJdbc()

                # Setup the SSO
                updateApplicationSecurity()

                #Run post setup steps - disable unused users, set theme, change superuser password if needed
                configureRepository(db_dict['password'])

                # Copy reports xml to webadmin folder
                webadminFolder = "%s/engine.ear/webadmin.war/webadmin/" % DIR_DEPLOY
                if not os.path.exists(webadminFolder):
                    os.makedirs(webadminFolder)
                shutil.copy2("%s/Reports.xml" % REPORTS_PACKAGE_DIR, webadminFolder)

                # Delete default properties files
                if os.path.exists(FILE_JASPER_DB_CONN):
                    os.remove(FILE_JASPER_DB_CONN)
                # Delete Jasper's Temp Folder
                # Delete Data Snapshots Folder,
                for path in (
                    '/tmp/jasperserver',
                    '/tmp/dataSnapshots',
                ):
                    if os.path.exists(path):
                        shutil.rmtree(path)

            # Restore previous version
            except:
                logging.error("Failed to complete the setup of the reports package!")
                logging.debug(traceback.format_exc())
                logging.debug("Restoring previous version")
                if not warUpdated and DB_EXIST:
                    restoreWAR()
                    restoreDB(db_dict, TEMP_PGPASS)
                raise

            # Start the ovirt-engine service
            utils.startEngine()

            # Restart the httpd service
            utils.restartHttpd()
            utils.storeConf(db_dict)
            print "Succesfully installed ovirt-engine-reports."
            print "The installation log file is available at: %s" % log_file

        else:
            logging.debug("user chose not to stop ovirt-engine")
            print "Installation stopped, Goodbye."
        logging.debug("main() ended")
    except:
        logging.error("Exception caught!")
        logging.error(traceback.format_exc())
        print sys.exc_info()[1]
        print "Error encountered while installing ovirt-engine-reports, please consult the log file: %s" % log_file
        rc = 1
    finally:
        shutil.rmtree(DIR_TEMP_SCHEDULE)
        resetReportsDatasourcePassword()
        if pghba_updated:
            utils.restorePgHba()
        return rc

if __name__ == "__main__":
    # Check permissions first
    _verifyUserPermissions()

    log_file = utils.initLogging(
        "ovirt-engine-reports-setup",
        "/var/log/ovirt-engine"
    )
    rc = main()
    sys.exit(rc)
