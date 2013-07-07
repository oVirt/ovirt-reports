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
import common_utils as utils
from decorators import transactionDisplay
import getpass
import shutil
import cracklib
import types
import tempfile
import re
import glob
import argparse

log_file = utils.initLogging("ovirt-engine-reports-setup", "/var/log/ovirt-engine")

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
ENGINE_DB_NAME = "engine"
ENGINE_HISTORY_DB_NAME = "ovirt_engine_history"

REPORTS_SERVER_DIR = "/usr/share/%s"  % JRS_PACKAGE_NAME
REPORTS_SERVER_BUILDOMATIC_DIR = "%s/buildomatic" % REPORTS_SERVER_DIR
FILE_JASPER_DB_CONN = "%s/default_master.properties" % REPORTS_SERVER_BUILDOMATIC_DIR

REPORTS_PACKAGE_DIR = "/usr/share/ovirt-engine-reports"
SSL2JKSTRUST = "%s/ssl2jkstrust.py" % REPORTS_PACKAGE_DIR
FILE_DB_DATA_SOURCE = "%s/reports/resources/reports_resources/JDBC/data_sources/ovirt.xml" % REPORTS_PACKAGE_DIR
DIR_REPORTS_CUSTOMIZATION="%s/server-customizations" % REPORTS_PACKAGE_DIR
DIR_OVIRT_THEME="%s/reports/resources/themes/ovirt-002dreports-002dtheme" % REPORTS_PACKAGE_DIR

REPORTS_JARS_DIR = "/usr/share/java/ovirt-engine-reports"

FILE_DEPLOY_VERSION = "/etc/ovirt-engine/jrs-deployment.version"
FILE_ENGINE_CONF_DEFAULTS = "/usr/share/ovirt-engine/conf/engine.conf.defaults"
FILE_ENGINE_CONF = "/etc/ovirt-engine/engine.conf"
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

DIR_TEMP_SCHEDUALE=tempfile.mkdtemp()

@transactionDisplay("Deploying Server")
def deployJs(db_dict):
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
            utils.dropDB(db_dict)
            DB_EXIST = False
            DB_EXISTED = True

        if isWarInstalled():
            shutil.rmtree(DIR_WAR)

        logging.debug("Linking Postgresql JDBC driver to %s/conf_source/db/postgresql/jdbc for installation" % REPORTS_SERVER_BUILDOMATIC_DIR)
        shutil.copyfile("/usr/share/java/postgresql-jdbc.jar", "%s/conf_source/db/postgresql/jdbc/postgresql-jdbc.jar" % REPORTS_SERVER_BUILDOMATIC_DIR)

        # No DB, install DB
        logging.debug("Installing")
        output, rc = utils.execExternalCmd("./%s minimal" % JRS_INSTALL_SCRIPT, True, "Failed installation of JasperReports Server")

        # FIXME: this is a temp WA for an issue in JS: running js-install always
        # returns 0
        if "BUILD FAILED" in output:
            raise Exception("Failed installation of JasperReports Server")

        logging.debug("Removing deployment of Postgresql JDBC driver and unused dodeploy file post installation")
        os.remove("%s/postgresql-jdbc.jar" % DIR_DEPLOY)
        os.remove("%s/WEB-INF/lib/postgresql-jdbc.jar" % DIR_WAR)
        os.remove("%s/%s.war.dodeploy" % (DIR_DEPLOY,JRS_APP_NAME))

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
    file_handler.editParam("js.dbName", db_dict["name"])
    file_handler.editParam("webAppNamePro", JRS_APP_NAME)
    file_handler.editParam("appServerDir", DIR_DEPLOY)
    file_handler.close()

def setReportsDatasource(db_dict):
    logging.debug("editing reports datasource file %s", FILE_DB_DATA_SOURCE)
    xml_editor = utils.XMLConfigFileHandler(FILE_DB_DATA_SOURCE)
    xml_editor.open()
    xml_editor.editParams({'/jdbcDataSource/connectionUrl':"jdbc:postgresql://%s:%s/%s" % (db_dict["host"],db_dict["port"],ENGINE_HISTORY_DB_NAME)})
    xml_editor.editParams({'/jdbcDataSource/connectionUser':db_dict["username"]})
    xml_editor.editParams({'/jdbcDataSource/connectionPassword':db_dict["password"]})
    xml_editor.close()

def resetReportsDatasourcePassword():
    logging.debug("editing reports datasource file %s", FILE_DB_DATA_SOURCE)
    xml_editor = utils.XMLConfigFileHandler(FILE_DB_DATA_SOURCE)
    xml_editor.open()
    xml_editor.editParams({'/jdbcDataSource/connectionPassword':""})
    xml_editor.close()

@transactionDisplay("Updating Redirect Servlet")
def updateServletDbRecord():
    '''
    update the RedirectServletReportsPage record in vdc_options
    '''

    # This is done due to jboss's bug: https://issues.jboss.org/browse/JBAS-9345
    # Since we cannot rely on jboss to redirect to a secure port, we insert
    # the Full url into the db.

    (protocol, fqdn, port) = getHostParams()
    hostUrl = "%s://%s:%s/%s" % (protocol, fqdn, port, JRS_APP_NAME)
    query ="update vdc_options set option_value='%s' where option_name='RedirectServletReportsPage';" % hostUrl
    cmd = [
        "/usr/bin/psql",
        "-U", db_dict["username"],
        "-h", db_dict["host"],
        "-p", db_dict["port"],
        "-d", ENGINE_DB_NAME,
        "-c", query,
    ]
    utils.execCmd(cmdList=cmd, failOnError=True, msg="Failed updating main page redirect")

@transactionDisplay("Setting DB connectivity")
def setDBConn():
    shutil.copyfile("%s/default_master.properties" % REPORTS_PACKAGE_DIR, FILE_JASPER_DB_CONN)
    if db_dict['password']:
        setDeploymentDetails(db_dict)
    else:
        raise OSError("Cannot find password for db")

def getDbDictFromOptions():
    db_dict = {"name"      : JRS_DB_NAME,
               "host"      : utils.getDbHostName(),
               "port"      : utils.getDbPort(),
               "username"  : utils.getDbAdminUser(),
               "password"  : utils.getPassFromFile(utils.getDbAdminUser())}
    return db_dict

def getDBStatus():
    global DB_EXIST
    if utils.dbExists(db_dict):
        logging.debug("Database %s seems to be alive" % db_dict["name"])
        DB_EXIST = True
    else:
        logging.debug("Could not query database (%s)" % db_dict["name"])

def getAdminPassword():
    """
    get the ovirt-engine-admin password from the user
    """
    passLoop = True
    while passLoop:
        userInput = getPassFromUser("Please choose a password for the admin users (ovirt-admin and superuser): ")
        # We do not need verification for the re-entered password
        userInput2 = getpass.getpass("Re-type password: ")
        if userInput == userInput2 and userInput != "":
            passLoop = False
        else:
            print "ERROR: passwords don't match"

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
        cmd = "./js-export.sh --output-dir %s --report-jobs /" % DIR_TEMP_SCHEDUALE
        utils.execExternalCmd(cmd, True, "Failed while exporting scheduale reports")

    except:
        logging.error("Exception caught, passing it along to main loop")
        raise

    finally:
        os.chdir(current_dir)

@transactionDisplay("Importing scheduled reports")
def importScheduale(inputDir=DIR_TEMP_SCHEDUALE):
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
def backupDB(db_dict):
    # pg_dump -C -E UTF8  --column-inserts --disable-dollar-quoting  --disable-triggers -U postgres --format=p -f $dir/$file  ovirt-engine
    logging.debug("DB Backup started")
    cmd = [
        PGDUMP_EXEC,
        "-C",
        "-E",
        "UTF8",
        "--column-inserts",
        "--disable-dollar-quoting",
        "--disable-triggers",
        "--format=p",
        "-U", db_dict["username"],
        "-h", db_dict["host"],
        "-p", db_dict["port"],
        "-f", FILE_TMP_SQL_DUMP,
        db_dict["name"],
    ]
    output, rc = utils.execCmd(cmdList=cmd, failOnError=True, msg=MSG_ERROR_BACKUP_DB)
    logging.debug("DB Backup completed successfully")
    logging.debug("DB Saved to %s", FILE_TMP_SQL_DUMP)

@transactionDisplay("Restoring reports DB")
def restoreDB(db_dict):
    #psql -U postgres -f <backup directory>/<backup_file>
    if os.path.exists(FILE_TMP_SQL_DUMP):
        logging.debug("DB Restore started")
        # Drop
        utils.dropDB(db_dict)
        # Restore
        cmd = [
            "/usr/bin/psql",
            "-U", db_dict["username"],
            "-h", db_dict["host"],
            "-p", db_dict["port"],
            "-f", FILE_TMP_SQL_DUMP,
        ]

        output, rc = utils.execCmd(cmdList=cmd, failOnError=True, msg=MSG_ERROR_RESTORE_DB)
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

    proxyEnabled = config["ENGINE_PROXY_ENABLED"]
    if proxyEnabled != None and proxyEnabled.lower() in ["true", "t", "yes", "y", "1"]:
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
    file_handler.close()
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
    logging.debug("editing datasources file")
    fd = open(FILE_JRS_DATASOURCES, "r")
    file_content = fd.read()
    fd.close()
    logging.debug("replace driver to module name")
    file_content = file_content.replace("<driver>postgresql-jdbc.jar</driver>", "<driver>postgresql</driver>")
    logging.debug("writing replaced content to %s" % FILE_JRS_DATASOURCES)
    fd = open(FILE_JRS_DATASOURCES, "w")
    fd.write(file_content)
    fd.close()
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
    (protocol, fqdn, port) = getHostParams()
    logging.debug("downloading certificates %s://%s:%s" % (protocol, fqdn, port))
    if protocol == 'https':
        utils.execExternalCmd(
            ' '.join(
                (
                    SSL2JKSTRUST,
                    '--host=%s' % fqdn,
                    '--port=%s' % port,
                    '--keystore=%s' % OVIRT_REPORTS_TRUST_STORE,
                    '--storepass=%s' % OVIRT_REPORTS_TRUST_STORE_PASS,
                )
            ),
            fail_on_error=True,
        )
    logging.debug("editing applicationContext-security-web file")
    hostValidateSessionUrl = "%s://%s:%s/OvirtEngineWeb/ValidateSession" % (protocol, fqdn, port)
    fd = open(FILE_APPLICATION_SECURITY_WEB, "r")
    file_content = fd.read()
    fd.close()
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
    fd = open(FILE_APPLICATION_SECURITY_WEB, "w")
    fd.write(file_content)
    fd.close()

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
    rc = 0
    preserveReportsJobs = False
    userPassword = False

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

            getDBStatus()

            # If this is a fresh install, get password from the user and set them in the users xml files
            if not DB_EXIST:
                userPassword = getAdminPassword()

            if not isWarInstalled() and DB_EXIST:
                logging.error("WAR Directory does not exist but the DB is up and running.")
                raise Exception(MSG_ERROR_DB_EXISTS % (db_dict["username"],
                                                       db_dict["host"],
                                                       db_dict["port"],
                                                       db_dict["name"]))

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
               backupWAR()
               backupDB(db_dict)

            # Catch failures on configuration
            try:
                # Export reports if we had a previous installation
                if preserveReportsJobs:
                    exportScheduale()

                if DB_EXIST:
                    savedDir = utils.exportUsers()

                # Execute js-ant to create DB and deploy WAR
                # May also set DB_EXIST to False if WAR is in need of an upgrade
                if not warUpdated or not isWarInstalled():
                    deployJs(db_dict)

                logging.debug("Database status: %s" % DB_EXIST)
                # Update oVirt-Engine vdc_options with reports relative url
                updateServletDbRecord()

                # If the userPassword var has been populated it means we need to edit the Admin xml file
                if userPassword:
                    editOvirtEngineAdminXml(userPassword)

                # Execute js-import to add reports to DB
                utils.importReports()

                if DB_EXIST:
                    logging.debug("Imporing users")
                    utils.importUsers(savedDir)

                # If this is a fresh install, we muck the password in the users xml files
                if userPassword:
                    editOvirtEngineAdminXml(MUCK_PASSWORD)

                # Link all files in ovirt-engine-reports/reports*/jar to /var/lib/jbosas/server/ovirt-engine-slimmed/deploy/ovirt-engine-reports/WEB-INF/lib
                customizeJs()

                # Import scheduale reports if they were previously existing
                if preserveReportsJobs:
                    scheduleDir = DIR_TEMP_SCHEDUALE
                    importScheduale(scheduleDir)

                # Edit Data Sources Driver Info
                updateDsJdbc()

                # Setup the SSO
                updateApplicationSecurity()

                #Run post setup steps - disable unused users, set theme, change superuser password if needed
                configureRepository(userPassword)

                # Delete default properties files
                if os.path.exists(FILE_JASPER_DB_CONN):
                    os.remove(FILE_JASPER_DB_CONN)

                # Copy reports xml to webadmin folder
                webadminFolder = "%s/engine.ear/webadmin.war/webadmin/" % DIR_DEPLOY
                if not os.path.exists(webadminFolder):
                    os.makedirs(webadminFolder)
                shutil.copy2("%s/Reports.xml" % REPORTS_PACKAGE_DIR, webadminFolder)

                # Delete Jasper's Temp Folder
                if os.path.exists("/tmp/jasperserver"):
                    shutil.rmtree("/tmp/jasperserver")

            # Restore previous version
            except:
                logging.error("Failed to complete the setup of the reports package!")
                logging.debug(traceback.format_exc())
                logging.debug("Restoring previous version")
                if not warUpdated and DB_EXIST:
                    restoreWAR()
                    restoreDB(db_dict)
                raise

            dwhInstalled = utils.dbExists({"name" : ENGINE_HISTORY_DB_NAME,
                                           "host" : db_dict["host"],
                                           "port" : db_dict["port"],
                                           "username" : db_dict["username"]})
            # Start the ovirt-engine service
            utils.startEngine()
            print "Succesfully installed ovirt-engine-reports."
            print "The installation log file is available at: %s" % log_file
            if not dwhInstalled:
                print "DWH has not been setup, please execute: \"ovirt-engine-dwh-setup\" before accessing the reports URL"

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
        shutil.rmtree(DIR_TEMP_SCHEDUALE)
        resetReportsDatasourcePassword()
        return rc

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
