#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013 Red Hat, Inc.
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


from constants import classproperty, osetupattrsclass, osetupattrs


from . import reportsconfig


@util.export
@util.codegen
class Const(object):
    PACKAGE_NAME = reportsconfig.PACKAGE_NAME
    PACKAGE_VERSION = reportsconfig.PACKAGE_VERSION
    DISPLAY_VERSION = reportsconfig.DISPLAY_VERSION
    RPM_VERSION = reportsconfig.RPM_VERSION
    RPM_RELEASE = reportsconfig.RPM_RELEASE
    SERVICE_NAME = 'ovirt-engine-reportsd'
    OVIRT_ENGINE_REPORTS_DB_BACKUP_PREFIX = 'reports'
    OVIRT_ENGINE_REPORTS_PACKAGE_NAME = 'ovirt-engine-reports'
    OVIRT_ENGINE_REPORTS_SETUP_PACKAGE_NAME = 'ovirt-engine-reports-setup'

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


@util.export
@util.codegen
class FileLocations(object):
    SYSCONFDIR = '/etc'
    DATADIR = '/usr/share'
    PKG_SYSCONF_DIR = reportsconfig.PKG_SYSCONF_DIR
    PKG_STATE_DIR = reportsconfig.PKG_STATE_DIR
    PKG_DATA_DIR = reportsconfig.PKG_DATA_DIR
    PKG_JAVA_DIR = reportsconfig.PKG_JAVA_DIR
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


class DWHDBEnv(object):
    """Sync with ovirt-dwh"""
    HOST = 'OVESETUP_DWH_DB/host'
    PORT = 'OVESETUP_DWH_DB/port'
    SECURED = 'OVESETUP_DWH_DB/secured'
    SECURED_HOST_VALIDATION = 'OVESETUP_DWH_DB/securedHostValidation'
    DATABASE = 'OVESETUP_DWH_DB/database'
    USER = 'OVESETUP_DWH_DB/user'
    PASSWORD = 'OVESETUP_DWH_DB/password'


# vim: expandtab tabstop=4 shiftwidth=4
