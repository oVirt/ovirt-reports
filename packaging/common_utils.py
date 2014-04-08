'''
common utils for ovirt-engine-reports-setup and ovirt-engine-dwh-setup
'''

import sys
import logging
import os
import traceback
import datetime
import re
import subprocess
import shutil
import libxml2
import types
import tempfile
import random
import string
import glob

from StringIO import StringIO

from decorators import transactionDisplay

from ovirt_engine import configfile

#text colors
RED = "\033[0;31m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
NO_COLOR = "\033[0m"
ENGINE_SERVICE_NAME = "ovirt-engine"

# CONST
EXEC_IP = "/sbin/ip"
EXEC_SU = "/bin/su"
EXEC_PSQL = '/usr/bin/psql'
EXEC_PGDUMP = '/usr/bin/pg_dump'
EXEC_SERVICE="/sbin/service"
EXEC_SYSTEMCTL="/bin/systemctl"
EXEC_CHKCONFIG="/sbin/chkconfig"

FILE_PG_PASS="/etc/ovirt-engine/.pgpass"
DIR_DATABASE_REPORTS_CONFIG = "/etc/ovirt-engine-reports/ovirt-engine-reports.conf.d/"
FILE_DATABASE_REPORTS_CONFIG = "10-setup-database.conf"
PGPASS_FILE_USER_LINE = "DB USER credentials"
PGPASS_FILE_ADMIN_LINE = "DB ADMIN credentials"
FILE_ENGINE_CONFIG_BIN="/usr/bin/engine-config"
JRS_PACKAGE_PATH="/usr/share/jasperreports-server"

ENGINE_DBSCRIPTS_PATH="/usr/share/ovirt-engine/dbscripts"

# Defaults
DB_ADMIN = "engine_reports"
DB_HOST = "localhost"
DB_PORT = "5432"

DIR_PGSQL_DATA = '/var/lib/pgsql/data'
FILE_PG_HBA = os.path.join(
    DIR_PGSQL_DATA,
    'pg_hba.conf'
)

# ERRORS
# TODO: Move all errors here and make them consistent
ERR_EXP_GET_CFG_IPS = "Error: could not get list of available IP addresses on this host"
ERR_EXP_GET_CFG_IPS_CODES = "Error: failed to get list of IP addresses"
ERR_RC_CODE = "Error: return Code is not zero"
ERR_WRONG_PGPASS_VALUE = "Error: unknown value type '%s' was requested"
ERR_PGPASS_VALUE_NOT_FOUND = "Error: requested value '%s' was not found \
in %s. Check oVirt Engine installation and that wildcards '*' are not used."
ERR_EDIT_CONFIG_LINE = "Error: unable to edit config line"
#set xml content & get node
ERR_EXP_UPD_XML_CONTENT="Unexpected error: XML query %s returned %s results"
ERR_EXP_UNKN_XML_OBJ="Unexpected error: given XML is neither string nor instance"

def _maskString(string, maskList=[]):
    """
    private func to mask passwords
    in utils
    """
    maskedStr = string
    for maskItem in maskList:
        maskedStr = maskedStr.replace(maskItem, "*"*8)

    return maskedStr

def getVDCOption(key):
    """
    Get option_value from vdc_options per given key
    """
    cmd = [
        FILE_ENGINE_CONFIG_BIN,
        "-g",
        key,
        "--cver=general",
        "-p",
        "/usr/share/ovirt-engine/conf/engine-config-install.properties",
    ]
    logging.debug("getting vdc option %s" % key)

    output, rc = execCmd(cmdList=cmd, failOnError=True, msg="Error: failed fetching configuration field %s" % key)
    logging.debug("Value of %s is %s" % (key, output))

    return output.rstrip()

def runFunction(func, displayString, *args):
    #keep relative spaceEN
    spaceLen = 70 - len(displayString)
    try:
        print "%s..." % (displayString),
        sys.stdout.flush()
        logging.debug("running %s" % (func.func_name))
        if len(args) > 0:
            func(args)
        else:
            func()
    except Exception, (instance):
        print ("[ " + _getColoredText("ERROR", RED) + " ]").rjust(spaceLen)
        logging.error(traceback.format_exc())
        raise Exception(instance)
    print ("[ " + _getColoredText("DONE", GREEN) + " ]").rjust(spaceLen - 3)

def generatePassword():
    return '%s%s' % (
        ''.join([random.choice(string.digits) for i in xrange(4)]),
        ''.join([random.choice(string.letters) for i in xrange(4)]),
    )

def _getColoredText (text, color):
    ''' gets text string and color
        and returns a colored text.
        the color values are RED/BLUE/GREEN/YELLOW
        everytime we color a text, we need to disable
        the color at the end of it, for that
        we use the NO_COLOR chars.
    '''
    return color + text + NO_COLOR

def getCurrentDateTime(is_utc=None):
    '''
    provides current date
    '''
    now = None
    if (is_utc is not None):
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now()
    return now.strftime("%Y_%m_%d_%H_%M_%S")

def initLogging(baseFileName, baseDir):
    '''
    initiates logging
    '''
    try:
        #in order to use UTC date for the log file, send True to getCurrentDateTime(True)
        log_file_name = "%s-%s.log" %(baseFileName, getCurrentDateTime())
        log_file = os.path.join(baseDir, log_file_name)
        if not os.path.isdir(os.path.dirname(log_file)):
            os.makedirs(os.path.dirname(log_file))
        level = logging.INFO
        level = logging.DEBUG
        hdlr = logging.FileHandler(filename = log_file, mode='w')
        fmts = '%(asctime)s::%(levelname)s::%(module)s::%(lineno)d::%(name)s:: %(message)s'
        dfmt = '%Y-%m-%d %H:%M:%S'
        fmt = logging.Formatter(fmts, dfmt)
        hdlr.setFormatter(fmt)
        logging.root.addHandler(hdlr)
        logging.root.setLevel(level)
        return log_file
    except:
        logging.error(traceback.format_exc())
        raise Exception()


class Service():
    def __init__(self, name):
        self.wasStopped = False
        self.wasStarted = False
        self.lastStateUp = False
        self.name = name

    def isServiceAvailable(self):
        if os.path.exists("/etc/init.d/%s" % self.name):
            return True
        return False

    def start(self, raiseFailure=False):
        logging.debug("starting %s", self.name)
        (output, rc) = self._serviceFacility("start")
        if rc == 0:
            self.wasStarted = True
        elif raiseFailure:
            raise Exception('Failed starting service %s' % self.name)

        return (output, rc)

    def stop(self, raiseFailure=False):
        logging.debug("stopping %s", self.name)
        (output, rc) = self._serviceFacility("stop")
        if rc == 0:
            self.wasStopped = True
            self.lastStateUp = False
        elif raiseFailure:
            raise Exception('Failed stopping service %s' % self.name)

        return (output, rc)

    def autoStart(self, start=True):
        mode = "on" if start else "off"
        cmd = [
            EXEC_CHKCONFIG,
            self.name,
            mode,
        ]
        execCmd(cmdList=cmd, failOnError=True)

    def conditionalStart(self, raiseFailure=False):
        """
        Will only start if wasStopped is set to True
        """
        if self.wasStopped and self.lastStateUp:
            logging.debug("Service %s was stopped. starting it again"%self.name)
            return self.start(raiseFailure)
        else:
            logging.debug(
                'Service was not stopped or was not running orignally, '
                'therefore we are not starting it.'
            )
            return ('', 0)

    def status(self):
        logging.debug("getting status for %s", self.name)
        (output, rc) = self._serviceFacility("status")
        self.lastStateUp = (rc == 0)
        return (output, rc)

    def _serviceFacility(self, action):
        """
        Execute the command "service NAME action"
        returns: output, rc
        """
        logging.debug("executing action %s on service %s", self.name, action)
        cmd = [
            EXEC_SERVICE,
            self.name,
            action
        ]
        return execCmd(cmdList=cmd, usePipeFiles=True)

    def available(self):
        logging.debug("checking if %s service is available", self.name)

        # Checks if systemd service available
        cmd = [
            EXEC_SYSTEMCTL,
            "show",
            "%s.service" % self.name
        ]
        if os.path.exists(EXEC_SYSTEMCTL):
            out, rc = execCmd(cmdList=cmd)
            sysd = "LoadState=loaded" in out
        else:
            sysd = False

        # Checks if systemV service available
        sysv = os.path.exists("/etc/init.d/%s" % self.name)

        return (sysd or sysv)

class ConfigFileHandler:
    def __init__(self, filepath):
        self.filepath = filepath
    def open(self):
        pass
    def close(self):
        pass
    def editParams(self, paramsDict):
        pass
    def delParams(self, paramsDict):
        pass

class TextConfigFileHandler(ConfigFileHandler):
    def __init__(self, filepath, sep="="):
        ConfigFileHandler.__init__(self, filepath)
        self.data = []
        self.sep = sep

    def open(self, useconfigfile=False):
        fd = file(self.filepath)
        self.data = fd.readlines()
        fd.close()
        self._useconfigfile = useconfigfile
        if self._useconfigfile:
            self._configfile = configfile.ConfigFile([self.filepath])

    def close(self):
        fd = file(self.filepath, 'w')
        for line in self.data:
            fd.write(line)
        fd.close()

    def getParam(self, param):
        value = None
        if self._useconfigfile:
            value = self._configfile.get(param)
        else:
            for line in self.data:
                if not re.match("\s*#", line):
                    found = re.match("\s*%s\s*\%s\s*(.+)$" % (param, self.sep), line)
                    if found:
                        value = found.group(1)
        return value

    def editParam(self, param, value):
        changed = False
        for i, line in enumerate(self.data[:]):
            if not re.match("\s*#", line):
                if re.match("\s*%s"%(param), line):
                    self.data[i] = "%s=%s\n"%(param, value)
                    changed = True
                    break
        if not changed:
            self.data.append("%s=%s\n"%(param, value))

    def editLine(self, regexp, newLine, failOnError=False, errMsg=ERR_EDIT_CONFIG_LINE):
        changed = False
        for i, line in enumerate(self.data[:]):
            if not re.match("\s*#", line):
                if re.match(regexp, line):
                    self.data[i] = newLine
                    changed = True
                    break
        if not changed:
            if failOnError:
                raise Exception(errMsg)
            else:
                logging.warn(errMsg)

    def delParams(self, paramsDict):
        pass

class XMLConfigFileHandler(ConfigFileHandler):
    def __init__(self, filepath):
        ConfigFileHandler.__init__(self, filepath)

    def open(self):
        libxml2.keepBlanksDefault(0)
        self.doc = libxml2.parseFile(self.filepath)
        self.ctxt = self.doc.xpathNewContext()

    def close(self):
        self.doc.saveFormatFile(self.filepath,1)
        self.doc.freeDoc()
        self.ctxt.xpathFreeContext()

    def xpathEval(self, xpath):
        return self.ctxt.xpathEval(xpath)

    def getNodeByProperty(self, prop_name, value):
        allNodes = self.doc.xpathEval("//*")
        for node in allNodes:
            if node.properties \
                and node.properties.name == prop_name \
                and node.properties.content == value:
                    return node
        return None

    def addNextNode(self, xmlNode, next_node_str):
        """ Add next_node_str as next sibling node to xmlNode """
        newXml = libxml2.parseDoc(next_node_str)
        newXmlNode = newXml.xpathEval('/*')[0]
        xmlNode.addNextSibling(newXmlNode)

    def editParams(self, paramsDict):
        editAllOkFlag = True
        if type(paramsDict) != types.DictType:
            raise Exception("Internal error: Illegal parameter type - paramsDict should be a dictionary, please report this issue")
        for key in paramsDict.iterkeys():
            editOkFlag = False
            nodeList = self.ctxt.xpathEval(key)
            if len(nodeList) == 1:
                nodeList[0].setContent(paramsDict[key])
                editOkFlag = True
            elif len(nodeList) == 0:
                parentNode = os.path.dirname(key)
                parentNodeList = self.ctxt.xpathEval(parentNode)
                if len(parentNodeList) == 1:
                    newNode = libxml2.newNode(os.path.basename(key))
                    newNode.setContent(paramsDict[key])
                    parentNodeList[0].addChild(newNode)
                    editOkFlag = True
            if not editOkFlag:
                logging.error("Failed editing %s" %(key))
                editAllOkFlag = False
        if not editAllOkFlag:
            return -1

    def delParams(self, paramsDict):
        pass

    def addNodes(self, xpath, xml):
        """
        Add a given xml into a specific point specified by the given xpath path into the xml object
        xml can be either a libxml2 instance or a string which contains a valid xml
        """
        parentNode = self.xpathEval(xpath)[0]
        if not parentNode:
            raise Exception(ERR_EXP_UPD_XML_CONTENT%(xpath, len(parentNode)))

        if isinstance(xml, str):
            newNode = libxml2.parseDoc(xml)
        elif isinstance(xml, libxml2.xmlDoc):
            newNode = xml
        else:
            raise Exception(ERR_EXP_UNKN_XML_OBJ)

        # Call xpathEval to strip the metadata string from the top of the new xml node
        parentNode.addChild(newNode.xpathEval('/*')[0])


def getXmlNode(xml, xpath):
    nodes = xml.xpathEval(xpath)
    if len(nodes) != 1:
        raise Exception("Unexpected error: XML query %s returned %s results" % (xpath, len(nodes)))
    return nodes[0]

def askQuestion(question=None, yesNo=False, options='', default=''):
    '''
    provides an interface that prompts the user
    to answer "yes/no" to a given question
    '''
    message = StringIO()
    ask_string = question
    if yesNo:
        options = '(yes|no)'
    if options:
        ask_string = "{ask_string} {options}".format(
            ask_string=ask_string,
            options=options,
        )
    if default is not '':
        ask_string = '{ask_string} [{default}] '.format(
            ask_string=ask_string,
            default=default,
        )
    ask_string = '{ask_string}: '.format(
        ask_string=ask_string,
    )
    logging.debug("asking user: %s" % ask_string)
    message.write(ask_string)
    message.seek(0)
    raw_answer = raw_input(message.read())
    logging.debug("user answered: %s"%(raw_answer))
    answer = raw_answer.lower()
    if yesNo:
        if answer == "yes" or answer == "y":
            return True
        elif answer == "no" or answer == "n":
            return False
        else:
            return askQuestion(question, yesNo=True)
    else:
        if (
            type(answer) != str or
            (len(answer) == 0 and default == '')
        ):
            print 'Not a valid answer. Try again'
            return askQuestion(question, options, default)
        elif len(answer) == 0:
            return default
        else:
            return answer

def askYesNo(question=None):
    '''
    provides an interface that prompts the user
    to answer "yes/no" to a given question
    '''
    return askQuestion(question, yesNo=True)

def execExternalCmd(command, failOnError=False, msg="Return code differs from 0"):
    '''
    executes a shell command, if failOnError is True, raises an exception
    '''
    logging.debug("cmd = %s" % (command))

    # Update os.environ with env if provided
    env = os.environ.copy()
    if not "PGPASSFILE" in env:
        env["PGPASSFILE"] = FILE_PG_PASS

    pi = subprocess.Popen(
        command,
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    out, err = pi.communicate()
    logging.debug("output = %s" % out)
    logging.debug("stderr = %s" % err)
    logging.debug("retcode = %s" % pi.returncode)
    output = out + err
    if failOnError and pi.returncode != 0:
        raise Exception(msg)
    return ("".join(output.splitlines(True)), pi.returncode)

def execSqlCmd(db_dict, sql_query, failOnError=False, err_msg="Failed running sql query", envDict={}):
    logging.debug("running sql query on host: %s, port: %s, db: %s, user: %s, query: \'%s\'." %
                  (db_dict["host"],
                   db_dict["port"],
                   db_dict['dbname'],
                   db_dict["username"],
                   sql_query))
    cmd = [
        "/usr/bin/psql",
        "-w",
        "--pset=tuples_only=on",
        "--set", "ON_ERROR_STOP=1",
        "--dbname", db_dict['dbname'],
        "--host", db_dict["host"],
        "--port", db_dict["port"],
        "--username", db_dict["username"],
        "-c", sql_query,
    ]
    return execCmd(cmdList=cmd, failOnError=failOnError, msg=err_msg, envDict=envDict)

def isEngineUp():
    '''
    checks if ovirt-engine is active
    '''
    logging.debug("checking the status of ovirt-engine")
    engine_service = Service(ENGINE_SERVICE_NAME)
    engine_service.status()
    return engine_service.lastStateUp

def stopEngine(answer=None):
    '''
    stops the ovirt-engine service
    '''
    logging.debug("checking ovirt-engine service")
    if isEngineUp():
        logging.debug("ovirt-engine is up and running")
        if answer is None:
            print "In order to proceed the installer must stop the ovirt-engine service"
            answer = askYesNo("Would you like to stop the ovirt-engine service")
        if answer:
            stopEngineService()
        else:
            logging.debug("User chose not to stop ovirt-engine")
            return False
    return True

@transactionDisplay("Stopping ovirt-engine")
def stopEngineService():
    logging.debug("Stopping ovirt-engine")
    engine_service = Service(ENGINE_SERVICE_NAME)
    engine_service.stop()

def startEngine():
    '''
    starts the ovirt-engine service
    '''
    if not isEngineUp():
        startEngineService()
    else:
        logging.debug("ovirt-engine is up, nothing to start")

@transactionDisplay("Starting ovirt-engine")
def startEngineService():
    logging.debug("Starting ovirt-engine")
    engine_service = Service(ENGINE_SERVICE_NAME)
    engine_service.start()

@transactionDisplay("Restarting httpd")
def restartHttpd():
    logging.debug("Restarting httpd")
    httpd_service = Service('httpd')
    httpd_service.stop()
    httpd_service.start()

def isPostgresUp():
    '''
    checks if the postgresql service is up and running
    '''
    logging.debug("checking the status of postgresql")
    postgres_service = Service('postgresql')
    postgres_service.status()
    return postgres_service.lastStateUp

def startPostgres():
    '''
    starts the postgresql service
    '''
    if not isPostgresUp():
        startPostgresService()

def stopPostgres():
    '''
    stops the postgresql service
    '''
    if isPostgresUp():
        stopPostgresService()

def restartPostgres():
    stopPostgres()
    startPostgres()

def startPostgresService():
    logging.debug("starting postgresql")
    postgres_service = Service('postgresql')
    postgres_service.start()

def stopPostgresService():
    logging.debug("stopping postgresql")
    postgres_service = Service('postgresql')
    postgres_service.stop()

def copyFile(source, destination):
    '''
    copies a file
    '''
    logging.debug("copying %s to %s" % (source, destination))
    shutil.copy2(source,destination)

def parseVersionString(string):
    """
    parse ovirt-engine version string and seperate it to version, minor version and release
    """
    VERSION_REGEX="(\d+\.\d+)\.(\d+)\-(\d+)"
    logging.debug("setting regex %s againts %s" % (VERSION_REGEX, string))
    found = re.search(VERSION_REGEX, string)
    if not found:
        raise Exception("Cannot parse version string, please report this error")
    version = found.group(1)
    minorVersion= found.group(2)
    release = found.group(3)

    return (version, minorVersion, release)

def getAppVersion(package):
    '''
    get the installed package version
    '''
    cmd = "rpm -q --queryformat %{VERSION}-%{RELEASE} " + package
    output, rc = execExternalCmd(cmd, True, "Failed to get package version & release")
    return output.rstrip()

@transactionDisplay("Importing reports")
def importReports(update=True):
    """
    import the reports
    """
    logging.debug("importing reports")
    current_dir = os.getcwd()
    os.chdir("%s/buildomatic" % JRS_PACKAGE_PATH)
    cmd = "./js-import.sh --input-dir /usr/share/ovirt-engine-reports/reports"
    if update:
        cmd = cmd + " --update"
    execExternalCmd(cmd, True, "Failed while importing reports")
    os.chdir(current_dir)

def fixNullUserPasswords(tempDir):
    logging.debug("fixNullUserPasswords started for %s" % tempDir)
    fixedFiles = []
    for f in glob.glob(tempDir + '/users/organization_1/*.xml'):
        xmlObj = XMLConfigFileHandler(f)
        xmlObj.open()
        node = getXmlNode(xmlObj, '/user/password')
        if node.getContent() == 'ENC<null>':
            fixedFiles.append(f)
            node.setContent('ENC<>')
        xmlObj.close()
    logging.debug("fixNullUserPasswords fixed: %s" % fixedFiles)

@transactionDisplay("Exporting current users")
def exportUsers():
    """
    export all users from jasper
    """
    logging.debug("exporting users from reports")
    current_dir = os.getcwd()

    # Create a temp directory
    tempDir =  tempfile.mkdtemp()
    logging.debug("temp directory: %s" % tempDir)

    os.chdir("%s/buildomatic" % JRS_PACKAGE_PATH)

    # Export all users from jasper into the temp directory
    logging.debug("Exporting users to %s" % tempDir)
    cmd = "./js-export.sh --output-dir %s --users --roles" % tempDir
    execExternalCmd(cmd, True, "Failed while exporting users")
    fixNullUserPasswords(tempDir)

    os.chdir(current_dir)
    return tempDir

def exportReportsRepository():
    """
    export all resources
    """
    logging.debug("exporting reports repository")
    current_dir = os.getcwd()

    # Create a temp directory
    tempDir =  tempfile.mkdtemp()
    logging.debug("temp directory: %s" % tempDir)

    os.chdir("%s/buildomatic" % JRS_PACKAGE_PATH)

    # Export all users from jasper into the temp directory
    logging.debug("Exporting repository to %s" % tempDir)
    cmd = "./js-export.sh --output-dir %s --everything" % tempDir
    execExternalCmd(cmd, True, "Failed while exporting users")

    os.chdir(current_dir)
    return tempDir

@transactionDisplay("Importing current users")
def importUsers(inputDir, update=True):
    """
    import all users from a given directory
    """
    logging.debug("importing users into reports")
    current_dir = os.getcwd()

    try:
        os.chdir("%s/buildomatic" % JRS_PACKAGE_PATH)

        # Export all users from jasper into the temp directory
        logging.debug("importing users from %s" % inputDir)
        cmd = "./js-import.sh --input-dir %s" % inputDir
        if update:
            cmd = cmd + " --update"
        execExternalCmd(cmd, True, "Failed while importing users")
    except:
        logging.error("exception caught, re-raising")
        raise
    finally:
        os.chdir(current_dir)

def restoreDefaultUsersXmlFiles(tempDir):
    logging.debug("restoring default users xml files")
    destDir = "/usr/share/ovirt-engine-reports/reports"
    shutil.rmtree("%s/users" % destDir)
    shutil.copytree("%s/users" % tempDir, "%s/users" % destDir)
    shutil.rmtree(tempDir)


def dbExists(db_dict, TEMP_PGPASS):

    exists = False
    owner = False
    hasData = False
    logging.debug("checking if %s db already exists" % db_dict['dbname'])
    env = {'ENGINE_PGPASS': TEMP_PGPASS}
    rc = -1
    if (
        db_dict['username'] == 'admin' and
        db_dict['password'] == 'dummy' and
        localHost(db_dict['host'])
    ):
        output, rc = runPostgresSuQuery(
            query='"select 1;"',
            database=db_dict['dbname'],
            failOnError=False,
        )
    else:
        output, rc = execSqlCmd(
            db_dict=db_dict,
            sql_query="select 1",
            envDict=env,
        )
    if rc == 0:
        exists = True
        if (
            db_dict['username'] == DB_ADMIN
        ):
            owner = True

        rc = -1
        if (
            db_dict['username'] == 'admin' and
            db_dict['password'] == 'dummy' and
            localHost(db_dict['host'])
        ):
            output, rc = runPostgresSuQuery(
                query='"select 1 from jiadhocdataview;"',
                database=db_dict['dbname'],
                failOnError=False,
            )
        else:
            output, rc = execSqlCmd(
                db_dict=db_dict,
                sql_query="select 1 from jiadhocdataview;",
                envDict=env,
            )
        if rc == 0:
            hasData = True

    return exists, owner, hasData

def getDbAdminUser():
    """
    Retrieve Admin user from .pgpass file on the system.
    Use default settings if file is not found.
    """
    return getDbConfig("admin") or DB_ADMIN

def getDbHostName():
    """
    Retrieve DB Host name from .pgpass file on the system.
    Use default settings if file is not found, or '*' was used.
    """

    return getDbConfig("host") or DB_HOST

def getDbPort():
    """
    Retrieve DB port number from .pgpass file on the system.
    """
    return getDbConfig("port") or DB_PORT

def getDbConfig(dbconf_param):
    """
    Generic function to retrieve values from admin line in .pgpass
    """
    # 'user' and 'admin' are the same fields, just different lines
    # and for different cases
    field = {'user' : 3, 'admin' : 3, 'host' : 0, 'port' : 1}
    if dbconf_param not in field.keys():
        raise Exception(ERR_WRONG_PGPASS_VALUE % dbconf_param)

    inDbAdminSection = False
    inDbUserSection = False
    if (os.path.exists(FILE_PG_PASS)):
        logging.debug("found existing pgpass file, fetching DB %s value" % dbconf_param)
        with open (FILE_PG_PASS) as pgPassFile:
            for line in pgPassFile:

                # find the line with "DB ADMIN"
                if PGPASS_FILE_ADMIN_LINE in line:
                    inDbAdminSection = True
                    continue

                if inDbAdminSection and dbconf_param == "admin" and \
                   not line.startswith("#"):
                    # Means we're on DB ADMIN line, as it's for all DBs
                    dbcreds = line.split(":", 4)
                    return dbcreds[field[dbconf_param]]

                # find the line with "DB USER"
                if PGPASS_FILE_USER_LINE in line:
                    inDbUserSection = True
                    continue

                # fetch the values
                if inDbUserSection:
                    # Means we're on DB USER line, as it's for all DBs
                    dbcreds = line.split(":", 4)
                    return dbcreds[field[dbconf_param]]

    return False

def getPassFromFile(username):
    '''
    get the password for specified user
    from /etc/ovirt-engine/.pgpass
    '''
    logging.debug("getting DB password for %s" % username)
    with open(FILE_PG_PASS, "r") as fd:
        for line in fd.readlines():
            if line.startswith("#"):
                continue
            # Max 4 splits, so if password includes ':' character, it
            # would still work fine.
            list = line.split(":", 4)
            if list[3] == username:
                logging.debug("found password for username %s" % username)
                return list[4].rstrip('\n')

    # If no pass was found, return None
    return None


def createDB(db_dict):
    createDatabase(db_dict['dbname'], db_dict['username'])


def createLang(db_dict, TEMP_PGPASS):
    try:
        cmd = [
            '/usr/bin/createlang',
            '--host=%s' % db_dict['host'],
            '--port=%s' % db_dict['port'],
            '--dbname=%s' % db_dict['dbname'],
            '--username=%s' % db_dict['username'],
            'plpgsql',
        ]

        execCmd(
            cmdList=cmd,
            failOnError=True,
            envDict={'ENGINE_PGPASS': TEMP_PGPASS},
        )
    except Exception as e:
        logging.debug("createLang: %s" % e)

def clearDB(db_dict, TEMP_PGPASS, log_file):
    """
    clears the given DB
    """
    createLang(db_dict, TEMP_PGPASS)
    logging.debug("Clearing db %s contents" % db_dict['dbname'])
    cmd = [
        '%s/%s' % (ENGINE_DBSCRIPTS_PATH, 'cleandb.sh'),
        '-s', db_dict['host'],
        '-d', db_dict['dbname'],
        '-u', db_dict['username'],
        '-p', db_dict['port'],
        '-l', log_file,
    ]
    execCmd(
        cmdList=cmd,
        failOnError=True,
        envDict={'ENGINE_PGPASS': TEMP_PGPASS},
    )

def getConfiguredIps():
    try:
        iplist = set()
        cmd = EXEC_IP + " addr"
        output, rc = execExternalCmd(cmd, True, ERR_EXP_GET_CFG_IPS_CODES)
        ipaddrPattern=re.compile('\s+inet (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}).+')
        list=output.splitlines()
        for line in list:
            foundIp = ipaddrPattern.search(line)
            if foundIp:
                if foundIp.group(1) != "127.0.0.1":
                    ipAddr = foundIp.group(1)
                    logging.debug("Found IP Address: %s"%(ipAddr))
                    iplist.add(ipAddr)
        return iplist
    except:
        logging.error(traceback.format_exc())
        raise Exception(ERR_EXP_GET_CFG_IPS)


def getHostName():
    cmd = [
        '/bin/hostname',
    ]
    out, rc = execCmd(cmdList=cmd, failOnError=True)
    return out.rstrip()


def localHost(hostname):
    # Create an ip set of possible IPs on the machine. Set has only unique values, so
    # there's no problem with union.
    # TODO: cache the list somehow? There's no poing quering the IP configuraion all the time.
    ipset = getConfiguredIps().union(set(["localhost", "127.0.0.1", getHostName()]))
    if hostname in ipset:
        return True
    return False

def createTempPgpass(db_dict, mode='all'):

    fd, pgpass = tempfile.mkstemp(
        prefix='pgpass',
        suffix='.tmp',
    )
    os.close(fd)
    os.chmod(pgpass, 0o600)
    with open(pgpass, 'w') as f:
        f.write(
            (
                '# DB USER credentials.\n'
                '{host}:{port}:{database}:{user}:{password}\n'
                '{host}:{port}:{database}:{engine_user}:{engine_pass}\n'
                '{host}:{port}:{engine_db}:{engine_user}:{engine_pass}\n'
                '{host}:{port}:{dwh_db}:{dwh_db_user}:{dwh_db_password}\n'
            ).format(
                host=db_dict['host'],
                port=db_dict['port'],
                database='*' if mode == 'all' else db_dict['dbname'],
                engine_db=db_dict['engine_db'],
                user=db_dict['username'],
                password=db_dict['password'],
                engine_user=db_dict['engine_user'],
                engine_pass=db_dict['engine_pass'],
                dwh_db=db_dict['dwh_database'],
                dwh_db_user=db_dict['dwh_db_user'],
                dwh_db_password=db_dict['dwh_db_password'],
            ),
        )

    return pgpass

def execCmd(
    cmdList,
    cwd=None,
    failOnError=False,
    msg='Return Code is not zero',
    maskList=[],
    useShell=False,
    usePipeFiles=False,
    envDict=None,
    stdIn=None,
    stdOut=None,
):
    """
    Run external shell command with 'shell=false'
    receives a list of arguments for command line execution
    """
    # All items in the list needs to be strings, otherwise the subprocess will fail
    cmd = [str(item) for item in cmdList]

    # We need to join cmd list into one string so we can look for passwords in it and mask them
    logCmd = _maskString((' '.join(cmd)), maskList)

    logging.debug("Executing command --> '%s' in working directory '%s'" % (logCmd, cwd or os.getcwd()))

    stdErrFD = subprocess.PIPE
    stdOutFD = subprocess.PIPE
    stdInFD = subprocess.PIPE

    stdInFile = None

    if usePipeFiles:
        (stdErrFD, stdErrFile) = tempfile.mkstemp(dir="/tmp")
        (stdOutFD, stdOutFile) = tempfile.mkstemp(dir="/tmp")
        (stdInFD, stdInFile) = tempfile.mkstemp(dir="/tmp")

    if stdIn is not None:
        logging.debug("input = %s"%(stdIn))
        if stdInFile is None:
            (stdInFD, stdInFile) = tempfile.mkstemp(dir="/tmp")
        os.write(stdInFD, stdIn)
        os.lseek(stdInFD, os.SEEK_SET, 0)

    if stdOut is not None:
        f = open(stdOut, 'w')
        stdOutFD = f.fileno()

    # Copy os.environ and update with envDict if provided
    env = os.environ.copy()
    env.update(envDict or {})
    if "ENGINE_PGPASS" in env.keys():
        env["PGPASSFILE"] = env["ENGINE_PGPASS"]
    else:
        env["PGPASSFILE"] = FILE_PG_PASS

    # We use close_fds to close any file descriptors we have so it won't be copied to forked childs
    proc = subprocess.Popen(
        cmd,
        stdout=stdOutFD,
        stderr=stdErrFD,
        stdin=stdInFD,
        cwd=cwd,
        shell=useShell,
        close_fds=True,
        env=env,
    )

    out, err = proc.communicate()
    if usePipeFiles:
        with open(stdErrFile, 'r') as f:
            err = f.read()
        os.remove(stdErrFile)

        with open(stdOutFile, 'r') as f:
            out = f.read()
        os.remove(stdOutFile)
        os.remove(stdInFile)

    logging.debug("output = %s"%(out))
    logging.debug("stderr = %s"%(err))
    logging.debug("retcode = %s"%(proc.returncode))
    output = str(out) + str(err)
    if failOnError and proc.returncode != 0:
        raise Exception(msg)
    return ("".join(output.splitlines(True)), proc.returncode)


def runPostgresSuCommand(command, failOnError=True, output=None):
    cmd = [
        EXEC_SU,
        '-l',
        'postgres',
        '-c',
        '{command}'.format(
            command=' '.join(command),
        )
    ]

    return execCmd(
        cmdList=cmd,
        failOnError=failOnError,
        stdOut=output,
    )

def runPostgresSuQuery(query, database=None, failOnError=True):
    logging.debug("starting runPostgresSuQuery database: %s query: %s" %
                  (database,
                   query))
    command = [
        EXEC_PSQL,
        '--pset=tuples_only=on',
        '--set',
        'ON_ERROR_STOP=1',
    ]
    if database is not None:
        command.extend(
            (
                '-d', database
            )
        )
    stdIn = None
    if isinstance(query, list) or isinstance(query, tuple):
        stdIn = '\n'.join(query)
    else:
        command.extend(
            (
                '-c', query,
            )
        )
    cmd = [
        EXEC_SU,
        '-l',
        'postgres',
        '-c',
        '{command}'.format(
            command=' '.join(command),
        )
    ]

    return execCmd(
        cmdList=cmd,
        failOnError=failOnError,
        stdIn=stdIn,
    )

_RE_POSTGRES_PGHBA_LOCAL = re.compile(
    flags=re.VERBOSE,
    pattern=r"""
        ^
        (?P<host>local)
        \s+
        .*
        \s+
        (?P<param>\w+)
        $
    """,
)

def configHbaIdent(orig='md5', newval='ident'):
    content = []
    logging.debug('Updating pghba postgres use')

    with open(FILE_PG_HBA, 'r') as pghba:
        for line in pghba.read().splitlines():
            matcher = _RE_POSTGRES_PGHBA_LOCAL.match(line)
            if matcher is not None:
                if matcher.group('param') == newval:
                    return False
                if matcher.group('param') == orig:
                    line = line.replace(matcher.group('param'), newval)
            content.append(line)

    with open(FILE_PG_HBA, 'w') as pghba:
        pghba.write('\n'.join(content))

    restartPostgres()
    return True

def setPgHbaIdent():
    return configHbaIdent()

def restorePgHba():
    return configHbaIdent('ident', 'md5')

def updatePgHba(username, database):
    content = []
    updated = False
    logging.debug('Updating pghba')
    with open(FILE_PG_HBA, 'r') as pghba:
        for line in pghba.read().splitlines():
            if username in line:
                return

            if line.startswith('host') and not updated:
                for address in ('0.0.0.0/0', '::0/0'):
                    content.append(
                        (
                            '{host:7} '
                            '{database:15} '
                            '{user:15} '
                            '{address:23} '
                            '{auth}'
                        ).format(
                            host='host',
                            user=username,
                            database=database,
                            address=address,
                            auth='md5',
                        )
                    )
                updated = True

            content.append(line)

    with open(FILE_PG_HBA, 'w') as pghba:
        pghba.write('\n'.join(content))

def createUser(user, password):
    if userExists(user):
        return

    logging.debug('Adding user {user}'.format(user=user))

    runPostgresSuQuery(
        query=(
            '"CREATE ROLE {user} with '
            'login encrypted password \'{password}\';"'
        ).format(
            user=user,
            password=password,
        )
    )


def createRole(database, username, password):
    createUser(
        user=username,
        password=password,
    )
    updatePgHba(username, database)
    restartPostgres()


def createDatabase(database, owner):
    runPostgresSuQuery(
        query=(
            (
                '"create database {database} '
                'encoding \'UTF8\' LC_COLLATE \'en_US.UTF-8\' '
                'LC_CTYPE \'en_US.UTF-8\' template template0 '
                'owner {owner};"'
            ).format(
                database=database,
                owner=owner,
            )
        )
    )


def updateDbOwner(db_dict):
    logging.debug('Updating DB owner')
    _RE_OWNER = re.compile(r'^([\w,.\(\)]+\s+)+OWNER TO (?P<owner>\w+).*$')
    out, rc = runPostgresSuCommand(
        command=(
            EXEC_PGDUMP,
            '-s',
            db_dict['dbname'],
        ),
    )
    sql_query_set = []
    sql_query_set.append(
        'ALTER DATABASE {database} OWNER TO {owner};'.format(
            database=db_dict['dbname'],
            owner=db_dict['username'],
        )
    )
    for line in out.splitlines():
        matcher = _RE_OWNER.match(line)
        if matcher is not None:
            sql_query_set.append(
                '{query}'.format(
                    query=line.replace(
                        'OWNER TO {orig}'.format(orig=matcher.group('owner')),
                        'OWNER TO {new}'.format(new=db_dict['username'])
                    )
                )
            )

    runPostgresSuQuery(
        query=sql_query_set,
        database=db_dict['dbname'],
    )

def escape(s, chars):
    ret = ''
    for c in s:
        if c in chars:
            ret += '\\'
        ret += c
    return ret

def storeConf(db_dict):
    if not os.path.exists(DIR_DATABASE_REPORTS_CONFIG):
        os.makedirs(DIR_DATABASE_REPORTS_CONFIG)
    with open(
        os.path.join(
            DIR_DATABASE_REPORTS_CONFIG,
            FILE_DATABASE_REPORTS_CONFIG
        ),
        'w'
    ) as rf:
        rf.write(
            (
                'REPORTS_DB_DATABASE={database}\n'
                'REPORTS_DB_USER={user}\n'
                'REPORTS_DB_PASSWORD="{password}"'
            ).format(
                database=db_dict['dbname'],
                user=db_dict['username'],
                password=escape(db_dict['password'], '"\\$'),
            )
        )


def userExists(user):
    sql_query = '"select 1 from pg_roles where rolname=\'{user}\';"'.format(
        user=user
    )

    output, rc = runPostgresSuQuery(sql_query)
    return '1' in output
