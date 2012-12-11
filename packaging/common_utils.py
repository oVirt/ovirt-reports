'''
common utils for ovirt-engine-reports-setup and ovirt-engine-dwh-setup
'''

import sys
import logging
import os
import traceback
import datetime
import re
from StringIO import StringIO
import subprocess
import shutil
import libxml2
import types
from decorators import transactionDisplay
import tempfile

#text colors
RED = "\033[0;31m"
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
NO_COLOR = "\033[0m"
ENGINE_SERVICE_NAME = "ovirt-engine"

# CONST
EXEC_IP = "/sbin/ip"
FILE_PG_PASS="/etc/ovirt-engine/.pgpass"
PGPASS_FILE_USER_LINE = "DB USER credentials"
PGPASS_FILE_ADMIN_LINE = "DB ADMIN credentials"
FILE_ENGINE_CONFIG_BIN="/usr/bin/engine-config"
JRS_PACKAGE_PATH="/usr/share/jasperreports-server"

# Defaults
DB_ADMIN = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

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

    def open(self):
        fd = file(self.filepath)
        self.data = fd.readlines()
        fd.close()

    def close(self):
        fd = file(self.filepath, 'w')
        for line in self.data:
            fd.write(line)
        fd.close()

    def getParam(self, param):
        value = None
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

def askYesNo(question=None):
    '''
    provides an interface that prompts the user
    to answer "yes/no" to a given question
    '''
    message = StringIO()
    ask_string = "%s? (yes|no): " % question
    logging.debug("asking user: %s" % ask_string)
    message.write(ask_string)
    message.seek(0)
    raw_answer = raw_input(message.read())
    logging.debug("user answered: %s"%(raw_answer))
    answer = raw_answer.lower()
    if answer == "yes" or answer == "y":
        return True
    elif answer == "no" or answer == "n":
        return False
    else:
        return askYesNo(question)

def execExternalCmd(command, fail_on_error=False, msg="Return code differs from 0"):
    '''
    executes a shell command, if fail_on_error is True, raises an exception
    '''
    logging.debug("cmd = %s" % (command))
    pi = subprocess.Popen(command, shell=True,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = pi.communicate()
    logging.debug("output = %s" % out)
    logging.debug("stderr = %s" % err)
    logging.debug("retcode = %s" % pi.returncode)
    output = out + err
    if fail_on_error and pi.returncode != 0:
        raise Exception(msg)
    return ("".join(output.splitlines(True)), pi.returncode)

def execSqlCmd(db_dict, sql_query, fail_on_error=False, err_msg="Failed running sql query"):
    logging.debug("running sql query on host: %s, port: %s, db: %s, user: %s, query: \'%s\'." %
                  (db_dict["host"],
                   db_dict["port"],
                   db_dict["name"],
                   db_dict["username"],
                   sql_query))
    cmd = [
        "/usr/bin/psql",
        "--pset=tuples_only=on",
        "--set", "ON_ERROR_STOP=1",
        "--dbname", db_dict["name"],
        "--host", db_dict["host"],
        "--port", db_dict["port"],
        "--username", db_dict["username"],
        "-c", sql_query,
    ]
    return execCmd(cmdList=cmd, failOnError=fail_on_error, msg=err_msg)

def isEngineUp():
    '''
    checks if ovirt-engine is active
    '''
    logging.debug("checking the status of ovirt-engine")
    cmd = "service %s status" % ENGINE_SERVICE_NAME
    output, rc = execExternalCmd(cmd, False, "Failed while checking for ovirt-engine service status")
    if " is running" in output:
        return True
    else:
        return False

def stopEngine():
    '''
    stops the ovirt-engine service
    '''
    logging.debug("checking ovirt-engine service")
    if isEngineUp():
        logging.debug("ovirt-engine is up and running")
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
    cmd = "service %s stop" % ENGINE_SERVICE_NAME
    logging.debug("Stopping ovirt-engine")
    execExternalCmd(cmd, True, "Failed while trying to stop the ovirt-engine service")

def startEngine():
    '''
    starts the ovirt-engine service
    '''
    if not isEngineUp():
        startEngineService()
    else:
        logging.debug("jobss is up. nothing to start")

@transactionDisplay("Starting ovirt-engine")
def startEngineService():
    cmd = "service %s start" % ENGINE_SERVICE_NAME
    logging.debug("Starting ovirt-engine")
    execExternalCmd(cmd, True, "Failed while trying to start the ovirt-engine service")

def isPostgresUp():
    '''
    checks if the postgresql service is up and running
    '''
    logging.debug("checking the status of postgresql")
    cmd = "service postgresql status"
    output, rc = execExternalCmd(cmd, False)
    if rc == 0:
        return True
    else:
        return False

def startPostgres():
    '''
    starts the postgresql service
    '''
    if not isPostgresUp():
        startPostgresService()

@transactionDisplay("Starting PostgresSql")
def startPostgresService():
    logging.debug("starting postgresql")
    cmd = "service postgresql start"
    execExternalCmd(cmd, True, "Failed while trying to start the postgresql service")

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

def dbExists(db_dict):
    logging.debug("checking if %s db already exists" % db_dict["name"])
    (output, rc) = execSqlCmd(db_dict, "select 1")
    if (rc != 0):
        return False
    else:
        return True

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

def dropDB(db_dict):
    """
    drops the given DB
    """
    logging.debug("dropping db %s" % db_dict["name"])
    cmd = "/usr/bin/dropdb -U %s %s" %(db_dict["username"], db_dict["name"])
    (output, rc) = execExternalCmd(cmd, True, "Error while removing database %s" % db_dict["name"])

def getConfiguredIps():
    try:
        iplist=set()
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

def localHost(hostname):
    # Create an ip set of possible IPs on the machine. Set has only unique values, so
    # there's no problem with union.
    # TODO: cache the list somehow? There's no poing quering the IP configuraion all the time.
    ipset = getConfiguredIps().union(set([ "localhost", "127.0.0.1"]))
    if hostname in ipset:
        return True
    return False

#TODO: Move all execution commands to execCmd
def execCmd(cmdList, cwd=None, failOnError=False, msg=ERR_RC_CODE, maskList=[], useShell=False, usePipeFiles=False, envDict={}):
    """
    Run external shell command with 'shell=false'
    receives a list of arguments for command line execution
    """
    # All items in the list needs to be strings, otherwise the subprocess will fail
    cmd = [str(item) for item in cmdList]

    logging.debug("Executing command --> '%s'"%(cmd))

    stdErrFD = subprocess.PIPE
    stdOutFD = subprocess.PIPE
    stdInFD = subprocess.PIPE

    if usePipeFiles:
        (stdErrFD, stdErrFile) = tempfile.mkstemp(dir="/tmp")
        (stdOutFD, stdOutFile) = tempfile.mkstemp(dir="/tmp")
        (stdInFD, stdInFile) = tempfile.mkstemp(dir="/tmp")

    # Update os.environ with env if provided
    env = os.environ.copy()
    if not "PGPASSFILE" in env.keys():
        env["PGPASSFILE"] = FILE_PG_PASS
    env.update(envDict)

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
    output = out + err
    if failOnError and proc.returncode != 0:
        raise Exception(msg)
    return ("".join(output.splitlines(True)), proc.returncode)
