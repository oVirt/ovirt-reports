#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013-2014 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


"""Constants."""


import os
import gettext
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


from otopi import util


from ovirt_engine_setup.constants import classproperty
from ovirt_engine_setup.constants import osetupattrsclass
from ovirt_engine_setup.constants import osetupattrs

from . import config


@util.export
@util.codegen
class Const(object):
    PACKAGE_NAME = config.PACKAGE_NAME
    PACKAGE_VERSION = config.PACKAGE_VERSION
    DISPLAY_VERSION = config.DISPLAY_VERSION
    RPM_VERSION = config.RPM_VERSION
    RPM_RELEASE = config.RPM_RELEASE
    SERVICE_NAME = 'ovirt-engine-reportsd'
    OVIRT_ENGINE_REPORTS_DB_BACKUP_PREFIX = 'reports'
    OVIRT_ENGINE_REPORTS_PACKAGE_NAME = 'ovirt-engine-reports'
    OVIRT_ENGINE_REPORTS_SETUP_PACKAGE_NAME = 'ovirt-engine-reports-setup'

    # sync with engine
    PKI_REPORTS_JBOSS_CERT_NAME = 'reports'
    PKI_REPORTS_APACHE_CERT_NAME = 'apache-reports'

    @classproperty
    def REPORTS_DB_ENV_KEYS(self):
        return {
            'host': DBEnv.HOST,
            'port': DBEnv.PORT,
            'secured': DBEnv.SECURED,
            'hostValidation': DBEnv.SECURED_HOST_VALIDATION,
            'user': DBEnv.USER,
            'password': DBEnv.PASSWORD,
            'database': DBEnv.DATABASE,
            'connection': DBEnv.CONNECTION,
            'pgpassfile': DBEnv.PGPASS_FILE,
            'newDatabase': DBEnv.NEW_DATABASE,
        }

    @classproperty
    def DEFAULT_REPORTS_DB_ENV_KEYS(self):
        return {
            'host': Defaults.DEFAULT_DB_HOST,
            'port': Defaults.DEFAULT_DB_PORT,
            'secured': Defaults.DEFAULT_DB_SECURED,
            'hostValidation': Defaults.DEFAULT_DB_SECURED_HOST_VALIDATION,
            'user': Defaults.DEFAULT_DB_USER,
            'password': Defaults.DEFAULT_DB_PASSWORD,
            'database': Defaults.DEFAULT_DB_DATABASE,
        }

    @classproperty
    def DWH_DB_ENV_KEYS(self):
        return {
            'host': DWHDBEnv.HOST,
            'port': DWHDBEnv.PORT,
            'secured': DWHDBEnv.SECURED,
            'hostValidation': DWHDBEnv.SECURED_HOST_VALIDATION,
            'user': DWHDBEnv.USER,
            'password': DWHDBEnv.PASSWORD,
            'database': DWHDBEnv.DATABASE,
            'connection': DWHDBEnv.CONNECTION,
            'pgpassfile': DWHDBEnv.PGPASS_FILE,
            'newDatabase': DWHDBEnv.NEW_DATABASE,
        }

    @classproperty
    def DEFAULT_DWH_DB_ENV_KEYS(self):
        return {
            'host': DWHDefaults.DEFAULT_DB_HOST,
            'port': DWHDefaults.DEFAULT_DB_PORT,
            'secured': DWHDefaults.DEFAULT_DB_SECURED,
            'hostValidation': DWHDefaults.DEFAULT_DB_SECURED_HOST_VALIDATION,
            'user': DWHDefaults.DEFAULT_DB_USER,
            'password': DWHDefaults.DEFAULT_DB_PASSWORD,
            'database': DWHDefaults.DEFAULT_DB_DATABASE,
        }


@util.export
@util.codegen
class Defaults(object):
    DEFAULT_DB_HOST = 'localhost'
    DEFAULT_DB_PORT = 5432
    DEFAULT_DB_DATABASE = 'ovirt_engine_reports'
    DEFAULT_DB_USER = 'ovirt_engine_reports'
    DEFAULT_DB_PASSWORD = ''
    DEFAULT_DB_SECURED = False
    DEFAULT_DB_SECURED_HOST_VALIDATION = False
    DEFAULT_KEY_SIZE = 2048

    DEFAULT_NETWORK_HTTP_PORT = 80
    DEFAULT_NETWORK_HTTPS_PORT = 443
    DEFAULT_NETWORK_JBOSS_HTTP_PORT = 8090
    DEFAULT_NETWORK_JBOSS_HTTPS_PORT = 8453
    DEFAULT_NETWORK_JBOSS_AJP_PORT = 8712
    DEFAULT_NETWORK_JBOSS_DEBUG_ADDRESS = '127.0.0.1:8797'


@util.export
@util.codegen
class DWHDefaults(object):
    DEFAULT_DB_HOST = ''
    DEFAULT_DB_PORT = 5432
    DEFAULT_DB_DATABASE = 'ovirt_engine_history'
    DEFAULT_DB_USER = 'ovirt_engine_history'
    DEFAULT_DB_PASSWORD = ''
    DEFAULT_DB_SECURED = False
    DEFAULT_DB_SECURED_HOST_VALIDATION = False


@util.export
@util.codegen
class FileLocations(object):
    SYSCONFDIR = '/etc'
    DATADIR = '/usr/share'
    PKG_SYSCONF_DIR = config.PKG_SYSCONF_DIR
    SERVICE_DEFAULTS = config.SERVICE_DEFAULTS
    SERVICE_VARS = config.SERVICE_VARS
    SERVICE_VARS_D = '%s.d' % config.SERVICE_VARS
    REPORTS_CONFIG_PROTOCOLS = os.path.join(
        SERVICE_VARS_D,
        '10-setup-protocols.conf',
    )
    REPORTS_SERVICE_CONFIG_JBOSS = os.path.join(
        SERVICE_VARS_D,
        '10-setup-jboss.conf',
    )
    PKG_STATE_DIR = config.PKG_STATE_DIR
    PKG_DATA_DIR = config.PKG_DATA_DIR
    PKG_JAVA_DIR = config.PKG_JAVA_DIR
    SSO_CONFIGURATION = os.path.join(
        PKG_SYSCONF_DIR,
        'sso.properties',
    )
    OVIRT_ENGINE_REPORTS_DB_BACKUP_DIR = os.path.join(
        PKG_STATE_DIR,
        'backups',
    )
    OVIRT_ENGINE_REPORTS_JASPER_MODULES = os.path.join(
        PKG_STATE_DIR,
        'modules',
    )
    OVIRT_ENGINE_REPORTS_JASPER_WAR = os.path.join(
        PKG_STATE_DIR,
        'ovirt-engine-reports.war',
    )
    OVIRT_ENGINE_REPORTS_JASPER_QUARTZ = os.path.join(
        OVIRT_ENGINE_REPORTS_JASPER_WAR,
        'WEB-INF',
        'js.quartz.properties',
    )
    OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG = os.path.join(
        PKG_STATE_DIR,
        'build-conf',
    )
    OVIRT_ENGINE_REPORTS_BUILDOMATIC_DBPROP = os.path.join(
        OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG,
        'master.properties',
    )
    OVIRT_ENGINE_JASPER_CUSTOMIZATION = os.path.join(
        PKG_DATA_DIR,
        'jasper-customizations',
    )
    OVIRT_ENGINE_WAR_PATCHES = os.path.join(
        PKG_DATA_DIR,
        'jasper-war-patches',
    )
    OVIRT_ENGINE_REPORTS_EXPORT = os.path.join(
        PKG_DATA_DIR,
        'ovirt-reports',
    )
    OVIRT_ENGINE_REPORTS_UI = os.path.join(
        PKG_DATA_DIR,
        'conf',
        'reports.xml',
    )
    JASPER_BUILDOMATIC_CONFIG_TEMPALTE = os.path.join(
        PKG_DATA_DIR,
        'conf',
        'jasper-master.properties.in',
    )

    HTTPD_CONF_OVIRT_ENGINE_REPORTS_TEMPLATE = os.path.join(
        PKG_DATA_DIR,
        'conf',
        'ovirt-engine-reports-proxy.conf.in',
    )
    DIR_HTTPD = os.path.join(
        SYSCONFDIR,
        'httpd',
    )
    HTTPD_CONF_OVIRT_ENGINE_REPORTS = os.path.join(
        DIR_HTTPD,
        'conf.d',
        'z-ovirt-engine-reports-proxy.conf',
    )

    JASPER_HOME = os.path.join(
        DATADIR,
        'jasperreports-server',
    )

    LEGACY_OVIRT_ENGINE_REPORTS_JASPER_WAR = os.path.join(
        DATADIR,
        'ovirt-engine',
        'ovirt-engine-reports.war',
    )

    LEGACY_OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG = os.path.join(
        'buildomatic',
        'build_conf',
    )

    LEGACY_OVIRT_ENGINE_REPORTS_BUILDOMATIC_DBPROP = os.path.join(
        LEGACY_OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG,
        'default',
        'master.properties',
    )

    OVIRT_ENGINE_LOCALSTATEDIR = config.ENGINE_LOCALSTATEDIR

    OVIRT_ENGINE_PKIDIR = config.PKG_PKI_DIR

    OVIRT_ENGINE_PKIKEYSDIR = os.path.join(
        OVIRT_ENGINE_PKIDIR,
        'keys',
    )
    OVIRT_ENGINE_PKICERTSDIR = os.path.join(
        OVIRT_ENGINE_PKIDIR,
        'certs',
    )
    OVIRT_ENGINE_PKIREQUESTSDIR = os.path.join(
        OVIRT_ENGINE_PKIDIR,
        'requests',
    )

    # These are generated by engine ca.py. If not found we do that
    # ourselves.
    OVIRT_ENGINE_PKI_REPORTS_JBOSS_KEY = os.path.join(
        OVIRT_ENGINE_PKIKEYSDIR,
        '%s.key.nopass' % Const.PKI_REPORTS_JBOSS_CERT_NAME,
    )
    OVIRT_ENGINE_PKI_REPORTS_JBOSS_CERT = os.path.join(
        OVIRT_ENGINE_PKICERTSDIR,
        '%s.cer' % Const.PKI_REPORTS_JBOSS_CERT_NAME,
    )

    # These are generated by engine ca.py. Never by us.
    OVIRT_ENGINE_PKI_APACHE_KEY = os.path.join(
        OVIRT_ENGINE_PKIKEYSDIR,
        'apache.key.nopass',
    )
    OVIRT_ENGINE_PKI_APACHE_CA_CERT = os.path.join(
        OVIRT_ENGINE_PKIDIR,
        'apache-ca.pem',
    )
    OVIRT_ENGINE_PKI_APACHE_CERT = os.path.join(
        OVIRT_ENGINE_PKICERTSDIR,
        'apache.cer',
    )

    # These are generated and used in case the engine-generated
    # apache pki is not found.
    OVIRT_ENGINE_PKI_REPORTS_APACHE_KEY = os.path.join(
        OVIRT_ENGINE_PKIKEYSDIR,
        '%s.key.nopass' % Const.PKI_REPORTS_APACHE_CERT_NAME,
    )
    OVIRT_ENGINE_PKI_REPORTS_APACHE_CA_CERT = os.path.join(
        OVIRT_ENGINE_PKIDIR,
        '%s-ca.pem' % Const.PKI_REPORTS_APACHE_CERT_NAME,
    )
    OVIRT_ENGINE_PKI_REPORTS_APACHE_CERT = os.path.join(
        OVIRT_ENGINE_PKICERTSDIR,
        '%s.cer' % Const.PKI_REPORTS_APACHE_CERT_NAME,
    )


@util.export
class Stages(object):
    CORE_ENABLE = 'osetup.reports.core.enable'
    DB_CONNECTION_SETUP = 'osetup.reports.db.connection.setup'
    DB_CREDENTIALS_AVAILABLE = 'osetup.reports.db.connection.credentials'
    DB_CONNECTION_CUSTOMIZATION = 'osetup.reports.db.connection.customization'
    DB_CONNECTION_AVAILABLE = 'osetup.reports.db.connection.available'
    DB_SCHEMA = 'osetup.reports.db.schema'
    JASPER_DEPLOY_EXPORT = 'osetup.reports.jasper.deploy.export'
    JASPER_DEPLOY_IMPORT = 'osetup.reports.jasper.deploy.import'
    JASPER_NAME_SET = 'osetup.reports.jasper.name.set'
    CA_AVAILABLE = 'osetup.pki.ca.available'
    PKI_MISC = 'osetup.pki.misc'

    # sync with engine
    ENGINE_CORE_ENABLE = 'osetup.engine.core.enable'


@util.export
@util.codegen
@osetupattrsclass
class CoreEnv(object):

    @osetupattrs(
        answerfile=True,
        postinstallfile=True,
        summary=True,
        description=_('Reports installation'),
    )
    def ENABLE(self):
        return 'OVESETUP_REPORTS_CORE/enable'


@util.export
@util.codegen
@osetupattrsclass
class ConfigEnv(object):

    JASPER_HOME = 'OVESETUP_REPORTS_CONFIG/jasperHome'

    @osetupattrs(
        answerfile=True,
    )
    def ADMIN_PASSWORD(self):
        return 'OVESETUP_REPORTS_CONFIG/adminPassword'

    LEGACY_REPORTS_WAR = 'OVESETUP_REPORTS_CONFIG/legacyReportsWar'

    KEY_SIZE = 'OVESETUP_REPORTS_CONFIG/keySize'

    # Eventual public http/s ports - either apache or jboss
    # Commented 'internal use' in engine, perhaps it means they should not
    # be set from answer file.
    PUBLIC_HTTP_PORT = 'OVESETUP_REPORTS_CONFIG/publicHttpPort'
    PUBLIC_HTTPS_PORT = 'OVESETUP_REPORTS_CONFIG/publicHttpsPort'

    # Proxy (apache) ports
    HTTP_PORT = 'OVESETUP_REPORTS_CONFIG/httpPort'
    HTTPS_PORT = 'OVESETUP_REPORTS_CONFIG/httpsPort'

    # jboss ports - used if proxy is not used
    JBOSS_HTTP_PORT = 'OVESETUP_REPORTS_CONFIG/jbossHttpPort'
    JBOSS_HTTPS_PORT = 'OVESETUP_REPORTS_CONFIG/jbossHttpsPort'

    # jboss AJP port - apache communicates with it over this one
    JBOSS_AJP_PORT = 'OVESETUP_REPORTS_CONFIG/jbossAjpPort'

    # Set to JBOSS_HTTP_PORT if developer mode, otherwise default to None.
    # Perhaps can be set and thus enable direct http/s access to jboss
    # even if proxy/ajp is enabled, didn't check that.
    JBOSS_DIRECT_HTTP_PORT = 'OVESETUP_REPORTS_CONFIG/jbossDirectHttpPort'
    JBOSS_DIRECT_HTTPS_PORT = 'OVESETUP_REPORTS_CONFIG/jbossDirectHttpsPort'

    JBOSS_DEBUG_ADDRESS = 'OVESETUP_REPORTS_CONFIG/jbossDebugAddress'
    JBOSS_NEEDED = 'OVESETUP_REPORTS_CONFIG/jbossNeeded'

    PKI_JBOSS_CSR_FILENAME = 'OVESETUP_REPORTS_CONFIG/pkiJbossCSRFilename'
    PKI_APACHE_CSR_FILENAME = 'OVESETUP_REPORTS_CONFIG/pkiApacheCSRFilename'


@util.export
@util.codegen
@osetupattrsclass
class JasperEnv(object):
    JASPER_NAME = 'OVESETUP_REPORTS_JASPER/jasperName'
    REPORTS_EXPORT = 'OVESETUP_REPORTS_JASPER/reportsExport'
    SAVED_REPORTS_URI = 'OVESETUP_REPORTS_JASPER/savedReportsUri'
    THEME = 'OVESETUP_REPORTS_JASPER/theme'


@util.export
@util.codegen
@osetupattrsclass
class DBEnv(object):

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Reports database host'),
    )
    def HOST(self):
        return 'OVESETUP_REPORTS_DB/host'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Reports database port'),
    )
    def PORT(self):
        return 'OVESETUP_REPORTS_DB/port'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Reports database secured connection'),
    )
    def SECURED(self):
        return 'OVESETUP_REPORTS_DB/secured'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Reports database host name validation'),
    )
    def SECURED_HOST_VALIDATION(self):
        return 'OVESETUP_REPORTS_DB/securedHostValidation'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Reports database name'),
    )
    def DATABASE(self):
        return 'OVESETUP_REPORTS_DB/database'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Reports database user name'),
    )
    def USER(self):
        return 'OVESETUP_REPORTS_DB/user'

    @osetupattrs(
        answerfile=True,
    )
    def PASSWORD(self):
        return 'OVESETUP_REPORTS_DB/password'

    CONNECTION = 'OVESETUP_REPORTS_DB/connection'
    STATEMENT = 'OVESETUP_REPORTS_DB/statement'
    PGPASS_FILE = 'OVESETUP_REPORTS_DB/pgPassFile'
    NEW_DATABASE = 'OVESETUP_REPORTS_DB/newDatabase'


@util.export
@util.codegen
@osetupattrsclass
class RemoveEnv(object):

    REMOVE_JASPER_ARTIFACTS = 'OVESETUP_REPORTS_REMOVE/jasperArtifacts'

    @osetupattrs(
        answerfile=True,
    )
    def REMOVE_DATABASE(self):
        return 'OVESETUP_REPORTS_REMOVE/database'


@util.export
@util.codegen
@osetupattrsclass
class ProvisioningEnv(object):

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Configure local Reports database'),
    )
    def POSTGRES_PROVISIONING_ENABLED(self):
        return 'OVESETUP_REPORTS_PROVISIONING/postgresProvisioningEnabled'


@util.export
@util.codegen
@osetupattrsclass
class RPMDistroEnv(object):
    PACKAGES = 'OVESETUP_REPORTS_RPMDISRO_PACKAGES'
    PACKAGES_SETUP = 'OVESETUP_REPORTS_RPMDISRO_PACKAGES_SETUP'


@util.export
@util.codegen
@osetupattrsclass
class ApacheEnv(object):
    HTTPD_CONF_OVIRT_ENGINE_REPORTS = \
        'OVESETUP_REPORTS_APACHE/configFileOvirtEngineReports'


@util.export
@util.codegen
@osetupattrsclass
class DWHDBEnv(object):
    """Sync with ovirt-dwh"""

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('DWH database host'),
    )
    def HOST(self):
        return 'OVESETUP_DWH_DB/host'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('DWH database port'),
    )
    def PORT(self):
        return 'OVESETUP_DWH_DB/port'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('DWH database secured connection'),
    )
    def SECURED(self):
        return 'OVESETUP_DWH_DB/secured'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('DWH database host name validation'),
    )
    def SECURED_HOST_VALIDATION(self):
        return 'OVESETUP_DWH_DB/securedHostValidation'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('DWH database name'),
    )
    def DATABASE(self):
        return 'OVESETUP_DWH_DB/database'

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('DWH database user name'),
    )
    def USER(self):
        return 'OVESETUP_DWH_DB/user'

    @osetupattrs(
        answerfile=True,
    )
    def PASSWORD(self):
        return 'OVESETUP_DWH_DB/password'

    CONNECTION = 'OVESETUP_DWH_DB/connection'
    STATEMENT = 'OVESETUP_DWH_DB/statement'
    PGPASS_FILE = 'OVESETUP_DWH_DB/pgPassFile'
    NEW_DATABASE = 'OVESETUP_DWH_DB/newDatabase'


@util.export
@util.codegen
@osetupattrsclass
class EngineCoreEnv(object):
    """Sync with ovirt-engine"""

    ENABLE = 'OVESETUP_ENGINE_CORE/enable'


@util.export
@util.codegen
class EngineFileLocations(object):
    """Sync with ovirt-engine"""

    OVIRT_ENGINE_SERVICE_CONFIGD = os.path.join(
        FileLocations.SYSCONFDIR,
        'ovirt-engine',
        'engine.conf.d'
    )
    OVIRT_ENGINE_SERVICE_CONFIG_REPORTS = os.path.join(
        OVIRT_ENGINE_SERVICE_CONFIGD,
        '10-setup-reports-access.conf'
    )


@util.export
@util.codegen
@osetupattrsclass
class EngineConfigEnv(object):
    """Sync with ovirt-engine"""

    @osetupattrs(
        answerfile=True,
        summary=True,
        description=_('Engine Host FQDN'),
        postinstallfile=True,
    )
    def ENGINE_FQDN(self):
        return 'OVESETUP_ENGINE_CONFIG/fqdn'


# vim: expandtab tabstop=4 shiftwidth=4
