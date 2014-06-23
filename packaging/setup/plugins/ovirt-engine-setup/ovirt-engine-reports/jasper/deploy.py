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


"""Schema plugin."""


import glob
import datetime
import tempfile
import os
import shutil
import gettext
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


import libxml2


from otopi import constants as otopicons
from otopi import util
from otopi import plugin
from otopi import transaction


from ovirt_engine import util as outil


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import reportsconstants as oreportscons
from ovirt_engine_setup import reportsutil as oreportsutil
from ovirt_engine_setup import util as osetuputil
from ovirt_engine_setup import database


@util.export
class Plugin(plugin.PluginBase):
    """Schema plugin."""

    class JasperSchemaTransaction(transaction.TransactionElement):

        def __init__(self, parent):
            self._parent = parent
            self._restore = []
            self._backup = None

            self._dbovirtutils = database.OvirtUtils(
                plugin=self._parent,
                dbenvkeys=oreportscons.Const.REPORTS_DB_ENV_KEYS,
            )

        def __str__(self):
            return _("Jasper Schema Transaction")

        def prepare(self):
            suffix = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

            for src in (
                oreportscons.FileLocations.
                OVIRT_ENGINE_REPORTS_JASPER_WAR,
                oreportscons.FileLocations.
                OVIRT_ENGINE_REPORTS_JASPER_MODULES,
                oreportscons.FileLocations.
                OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG,
            ):
                if os.path.exists(src):
                    dst = '%s.%s' % (src, suffix)
                    self._restore.append(dict(src=src, dst=dst))
                    os.rename(src, dst)
                else:
                    dst = None
                    self._restore.append(dict(src=src, dst=dst))

            if not self._parent.environment[
                oreportscons.DBEnv.NEW_DATABASE
            ]:
                self._backup = self._dbovirtutils.backup(
                    dir=(
                        oreportscons.FileLocations.
                        OVIRT_ENGINE_REPORTS_DB_BACKUP_DIR
                    ),
                    prefix=(
                        oreportscons.Const.
                        OVIRT_ENGINE_REPORTS_DB_BACKUP_PREFIX
                    ),
                )

            self._dbovirtutils.clearDatabase()

        def abort(self):
            self._parent.logger.info(_('Rolling back Reports database schema'))
            try:
                self._parent.logger.info(
                    _('Clearing Reports database {database}').format(
                        database=self._parent.environment[
                            oreportscons.DBEnv.DATABASE
                        ],
                    )
                )
                self._dbovirtutils.clearDatabase()
                if self._backup is not None and os.path.exists(self._backup):
                    self._parent.logger.info(
                        _('Restoring Reports database {database}').format(
                            database=self._parent.environment[
                                oreportscons.DBEnv.DATABASE
                            ],
                        )
                    )
                    self._dbovirtutils.restore(backupFile=self._backup)
            except Exception as e:
                self._parent.logger.debug(
                    'Exception during Reports database restore',
                    exc_info=True,
                )
                self._parent.logger.error(
                    _('Reports database rollback failed: {error}').format(
                        error=e,
                    )
                )

            self._parent.logger.info(_('Rolling back Reports files'))
            for entry in self._restore:
                try:
                    if entry['dst'] is not None:
                        if os.path.exists(entry['src']):
                            shutil.rmtree(entry['src'])
                        os.rename(entry['dst'], entry['src'])
                except Exception as e:
                    self._parent.logger.debug(
                        'Exception during rename %s->%s',
                        entry['dst'],
                        entry['src'],
                        exc_info=True,
                    )
                    self._parent.logger.error(
                        _(
                            "File rollback '{src}' to '{dst}' failed: "
                            "{error}"
                        ).format(
                            src=entry['dst'],
                            dst=entry['src'],
                            error=e,
                        )
                    )

        def commit(self):
            for entry in self._restore:
                if entry['dst'] is not None and os.path.exists(entry['dst']):
                    shutil.rmtree(entry['dst'])

    def _buildJs(self, cmd, config, noSuffix=False):

        try:
            myumask = os.umask(0o022)

            rc, stdout, stderr = self.execute(
                args=(
                    './js-ant',
                    '-DmasterPropsSource=%s' % config,
                    (
                        cmd if noSuffix
                        else '%s-%s' % (
                            cmd,
                            self.environment[
                                oreportscons.JasperEnv.JASPER_NAME
                            ],
                        )
                    ),
                ),
                envAppend={
                    'JAVA_HOME': self.environment[
                        osetupcons.ConfigEnv.JAVA_HOME
                    ],
                    'ANT_OPTS': '-Djava.io.tmpdir=%s' % self._javatmp,
                },
                cwd=os.path.join(
                    self.environment[
                        oreportscons.ConfigEnv.JASPER_HOME
                    ],
                    'buildomatic',
                ),
            )

            # FIXME: this is a temp WA for an issue in JS
            # running js-install always returns 0
            if 'BUILD FAILED' in '\n'.join(stdout + stderr):
                raise RuntimeError(
                    _("Cannot build Jasper '{command}'").format(
                        command=cmd,
                    )
                )
        finally:
            os.umask(myumask)

            #
            # buildomatic config
            # contains sensitive information
            # for some reason jasper recreate
            # it, so we cannot be fully secured while
            # running.
            #
            if os.path.exists(
                oreportscons.FileLocations.
                OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
            ):
                os.chmod(
                    (
                        oreportscons.FileLocations.
                        OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
                    ),
                    0o700,
                )

    def _workaroundUsersNullPaswords(self, src):
        for f in glob.glob(os.path.join(src, 'users', '*.xml')):
            with oreportsutil.XMLDoc(f) as xml:
                for node in xml.xpath.xpathEval('/user/password'):
                    if node.getContent() == 'ENC<null>':
                        node.setContent('ENC<>')

    def _jasperConfiguration(self):
        config = os.path.join(self._temproot, 'config')
        with open(config, 'w') as f:
            f.write(
                outil.processTemplate(
                    template=(
                        oreportscons.FileLocations.
                        JASPER_BUILDOMATIC_CONFIG_TEMPALTE
                    ),
                    subst={
                        '@PKG_STATE_DIR@': (
                            oreportscons.FileLocations.PKG_STATE_DIR
                        ),
                        '@REPORTS_DB_HOST@': self.environment[
                            oreportscons.DBEnv.HOST
                        ],
                        '@REPORTS_DB_PORT@': self.environment[
                            oreportscons.DBEnv.PORT
                        ],
                        '@REPORTS_DB_USER@': self.environment[
                            oreportscons.DBEnv.USER
                        ],
                        '@REPORTS_DB_PASSWORD@': self.environment[
                            oreportscons.DBEnv.PASSWORD
                        ],
                        '@REPORTS_DB_DATABASE@': self.environment[
                            oreportscons.DBEnv.DATABASE
                        ],
                    },
                )
            )
        return config

    def _prepareOvirtReports(self):

        reportsImport = os.path.join(self._temproot, 'ovirt-reports')

        shutil.copytree(
            self.environment[oreportscons.JasperEnv.REPORTS_EXPORT],
            reportsImport,
            symlinks=False,
        )

        if self.environment[oreportscons.ConfigEnv.ADMIN_PASSWORD] is not None:
            with oreportsutil.XMLDoc(
                os.path.join(
                    reportsImport,
                    'users',
                    'admin.xml',
                )
            ) as xml:
                xml.setNodesContent(
                    '/user/password',
                    self.environment[
                        oreportscons.ConfigEnv.ADMIN_PASSWORD
                    ],
                )
                xml.setNodesContent(
                    '/user/enabled',
                    'true',
                )

        dwhdatasource = os.path.join(
            reportsImport,
            'resources',
            'reports_resources',
            'JDBC',
            'data_sources',
            'ovirt.xml',
        )
        if self._dwhdatasource:
            shutil.copyfile(
                self._dwhdatasource,
                dwhdatasource,
            )
            if (
                self.environment[oreportscons.JasperEnv.JASPER_NAME] == 'pro'
            ):
                with oreportsutil.XMLDoc(dwhdatasource) as xml:
                    node = xml.xpath.xpathEval('/jdbcDataSource/folder')[0]
                    nodeContent = node.getContent()
                    nodeContent = nodeContent.replace(
                        os.path.join(
                            '/',
                            self._reportsProRelativePath,
                        ),
                        ''
                    )
                    node.setContent(nodeContent)
        else:
            with oreportsutil.XMLDoc(dwhdatasource) as xml:
                xml.setNodesContent(
                    '/jdbcDataSource/connectionUrl',
                    'jdbc:postgresql://%s:%s/%s?%s' % (
                        self.environment[
                            oreportscons.DWHDBEnv.HOST
                        ],
                        self.environment[
                            oreportscons.DWHDBEnv.PORT
                        ],
                        self.environment[
                            oreportscons.DWHDBEnv.DATABASE
                        ],
                        '&'.join(
                            s for s in (
                                'ssl=true'
                                if self.environment[
                                    oreportscons.DWHDBEnv.SECURED
                                ] else '',

                                (
                                    'sslfactory='
                                    'org.postgresql.ssl.NonValidatingFactory'
                                )
                                if not self.environment[
                                    oreportscons.DWHDBEnv.
                                    SECURED_HOST_VALIDATION
                                ] else ''
                            ) if s
                        ),
                    ),
                )
                xml.setNodesContent(
                    '/jdbcDataSource/connectionUser',
                    self.environment[
                        oreportscons.DWHDBEnv.USER
                    ],
                )
                xml.setNodesContent(
                    '/jdbcDataSource/connectionPassword',
                    self.environment[
                        oreportscons.DWHDBEnv.PASSWORD
                    ],
                )

        return reportsImport

    def _checkDatabaseOwnership(self):
        statement = database.Statement(
            dbenvkeys=oreportscons.Const.REPORTS_DB_ENV_KEYS,
            environment=self.environment,
        )
        result = statement.execute(
            statement="""
                select
                    nsp.nspname as object_schema,
                    cls.relname as object_name,
                    rol.rolname as owner,
                    case cls.relkind
                        when 'r' then 'TABLE'
                        when 'i' then 'INDEX'
                        when 'S' then 'SEQUENCE'
                        when 'v' then 'VIEW'
                        when 'c' then 'TYPE'
                    else
                        cls.relkind::text
                    end as object_type
                from
                    pg_class cls join
                    pg_roles rol on rol.oid = cls.relowner join
                    pg_namespace nsp on nsp.oid = cls.relnamespace
                where
                    nsp.nspname not in ('information_schema', 'pg_catalog') and
                    nsp.nspname not like 'pg_%%' and
                    rol.rolname != %(user)s
                order by
                    nsp.nspname,
                    cls.relname
            """,
            args=dict(
                user=self.environment[oreportscons.DBEnv.USER],
            ),
            ownConnection=True,
            transaction=False,
        )
        if len(result) > 0:
            raise RuntimeError(
                _(
                    'Cannot upgrade the Reports database schema due to wrong '
                    'ownership of some database entities.\n'
                    'Please execute: {command}\n'
                    'Using the password of the "postgres" user.'
                ).format(
                    command=(
                        '{cmd} '
                        '-s {server} '
                        '-p {port} '
                        '-d {db} '
                        '-f postgres '
                        '-t {user}'
                    ).format(
                        cmd=(
                            osetupcons.FileLocations.
                            OVIRT_ENGINE_DB_CHANGE_OWNER
                        ),
                        server=self.environment[oreportscons.DBEnv.HOST],
                        port=self.environment[oreportscons.DBEnv.PORT],
                        db=self.environment[oreportscons.DBEnv.DATABASE],
                        user=self.environment[oreportscons.DBEnv.USER],
                    ),
                )
            )

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)
        self._oreportsutil = None
        self._temproot = None
        self._quartzprops = None
        self._users = None
        self._jobs = None
        self._dwhdatasource = None
        self._savedReports = None
        self._reportsProRelativePath = ''

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self._oreportsutil = oreportsutil.JasperUtil(plugin=self)
        self._temproot = tempfile.mkdtemp()
        self._javatmp = os.path.join(self._temproot, 'tmp')
        os.mkdir(self._javatmp)

        self.environment.setdefault(
            oreportscons.JasperEnv.REPORTS_EXPORT,
            oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_EXPORT
        )
        self.environment.setdefault(
            oreportscons.JasperEnv.SAVED_REPORTS_URI,
            '/saved_reports'
        )
        self.environment.setdefault(
            oreportscons.JasperEnv.THEME,
            'ovirt-reports-theme'
        )
        self.environment.setdefault(
            oreportscons.ConfigEnv.LEGACY_REPORTS_WAR,
            oreportscons.FileLocations.LEGACY_OVIRT_ENGINE_REPORTS_JASPER_WAR
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_SETUP,
    )
    def _setup(self):
        self.command.detect('patch')

    @plugin.event(
        stage=plugin.Stages.STAGE_VALIDATION,
        condition=lambda self: (
            self.environment[oreportscons.CoreEnv.ENABLE]
        ),
        after=(
            oreportscons.Stages.DB_CREDENTIALS_AVAILABLE,
        ),
    )
    def _validation(self):
        if not self.environment[
            oreportscons.DBEnv.NEW_DATABASE
        ]:
            self._checkDatabaseOwnership()
        else:
            if self.environment.get(
                oreportscons.DWHDBEnv.PASSWORD,
                None,
            ) is None:
                raise RuntimeError(
                    _(
                        'oVirt Data Warehouse connection details '
                        'are not available'
                    )
                )

        #
        # jasper build system places password in property file
        # sometime with escape and sometime without
        # do not allow special characters of property files
        #
        for c in self.environment[oreportscons.DBEnv.PASSWORD]:
            chars = ':=\\ $'
            if c in chars:
                raise RuntimeError(
                    _(
                        'Jasper database password contains '
                        'characters ({chars}) that are not '
                        'supported by Jasper'
                    ).format(
                        chars=chars,
                    )
                )

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.JASPER_NAME_SET,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def _jasper_name(self):
        install = glob.glob(
            os.path.join(
                self.environment[oreportscons.ConfigEnv.JASPER_HOME],
                'buildomatic',
                'conf_source',
                'ie*',
            )
        )
        if len(install) != 1:
            raise RuntimeError(
                _(
                    'Unexpected jasper installation, '
                    'buildomatic lib folder is missing'
                )
            )
        self.environment[
            oreportscons.JasperEnv.JASPER_NAME
        ] = os.path.basename(install[0]).replace(
            'ie', ''
        ).lower()

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.JASPER_DEPLOY_EXPORT,
        condition=lambda self: (
            self.environment[oreportscons.CoreEnv.ENABLE] and
            not self.environment[oreportscons.DBEnv.NEW_DATABASE]
        ),
        before=(
            oreportscons.Stages.DB_SCHEMA,
        ),
        after=(
            oreportscons.Stages.JASPER_NAME_SET,
        ),
    )
    def _export(self):
        config = self._jasperConfiguration()
        self._quartzprops = os.path.join(self._temproot, 'quartzprops')

        if (
            os.path.exists(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_WAR
            )
        ):
            shutil.copyfile(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_QUARTZ,
                self._quartzprops,
            )
        elif (
            os.path.exists(
                self.environment[oreportscons.ConfigEnv.LEGACY_REPORTS_WAR]
            )
        ):
            shutil.copyfile(
                os.path.join(
                    self.environment[
                        oreportscons.ConfigEnv.LEGACY_REPORTS_WAR
                    ],
                    'WEB-INF',
                    'js.quartz.properties'
                ),
                self._quartzprops,
            )

        else:
            raise RuntimeError(
                _('Could not detect Jasper war folder')
            )

        self.logger.info(
            _("Regenerating Jasper's build configuration files")
        )

        self._buildJs(config=config, cmd='gen-config', noSuffix=True)

        self.logger.info(_('Exporting data out of Jasper'))

        if (
            self.environment[oreportscons.JasperEnv.JASPER_NAME] == 'pro'
        ):
            self._reportsProRelativePath = 'organizations/organization_1'

        everything = self._oreportsutil.jsexport(
            what='everything',
            args=(
                '--everything',
            ),
        )
        if os.path.exists(
            os.path.join(
                everything,
                os.path.join(
                    'resources',
                    self._reportsProRelativePath,
                    self.environment[
                        oreportscons.JasperEnv.SAVED_REPORTS_URI
                    ],
                )
            )
        ):
            self._savedReports = self._oreportsutil.jsexport(
                what='savedReports',
                args=(
                    '--uris',
                    os.path.join(
                        '/',
                        self._reportsProRelativePath,
                        self.environment[
                            oreportscons.JasperEnv.SAVED_REPORTS_URI
                        ],
                    ),
                ),
            )
        self._jobs = self._oreportsutil.jsexport(
            what='jobs',
            args=(
                '--report-jobs', '/',
            ),
        )
        self._users = self._oreportsutil.jsexport(
            what='users',
            args=(
                '--users',
                '--roles',
            ),
        )
        dwhdatasourceexport = self._oreportsutil.jsexport(
            what='dwhdatasourceexport',
            args=(
                '--uris',
                os.path.join(
                    '/',
                    self._reportsProRelativePath,
                    'reports_resources',
                    'JDBC',
                    'data_sources',
                    'ovirt',
                ),
            ),
        )
        #
        # due to os.path.join considering any path starting with '/'
        # to be a new absulote path, had to concat the path strings.
        #
        self._dwhdatasource = os.path.join(
            dwhdatasourceexport,
            'resources',
            self._reportsProRelativePath,
            'reports_resources',
            'JDBC',
            'data_sources',
            'ovirt.xml',
        )

        self._workaroundUsersNullPaswords(self._users)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.DB_SCHEMA,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            oreportscons.Stages.JASPER_NAME_SET,
        ),
    )
    def _deploy(self):
        standalone = os.path.join(
            oreportscons.FileLocations.PKG_STATE_DIR,
            'standalone',
        )

        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            self.JasperSchemaTransaction(
                parent=self,
            )
        )

        config = self._jasperConfiguration()

        #
        # no way to tell jasper direct war
        # location.
        #
        if os.path.exists(standalone):
            shutil.rmtree(standalone)
        os.mkdir(standalone)
        os.symlink('..', os.path.join(standalone, 'deployments'))

        self.logger.info(_('Deploying Jasper'))
        for cmd in (
            'init-js-db',
            'import-minimal',
            'deploy-webapp',
        ):
            self._buildJs(config=config, cmd=cmd)

        if os.path.exists(standalone):
            shutil.rmtree(standalone)
        for f in glob.glob(
            os.path.join(
                oreportscons.FileLocations.PKG_STATE_DIR,
                '*.war.dodeploy',
            )
        ):
            os.unlink(f)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.JASPER_DEPLOY_IMPORT,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            oreportscons.Stages.DB_SCHEMA,
            oreportscons.Stages.JASPER_NAME_SET,
        ),
    )
    def _import(self):

        self.logger.info(_('Importing data into Jasper'))

        if self._quartzprops:
            shutil.copyfile(
                self._quartzprops,
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_QUARTZ,
            )
            os.chmod(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_QUARTZ,
                0o644,
            )

        if self._users:
            self._oreportsutil.jsimport(self._users)

        if self._savedReports:
            self._oreportsutil.jsimport(self._savedReports)

        self._oreportsutil.jsimport(self._prepareOvirtReports())

        #
        # We import users twice because we need permissions to be
        # preserved as well as users passwords reset after importing
        # reports in previous step.
        #
        if self._users:
            self._oreportsutil.jsimport(self._users)

        if self._jobs:
            self._oreportsutil.jsimport(self._jobs)

        self.logger.info(_('Configuring Jasper Java resources'))

        for f in glob.glob(
            os.path.join(
                oreportscons.FileLocations.PKG_JAVA_DIR,
                '*.jar',
            )
        ):
            shutil.copy2(
                f,
                os.path.join(
                    oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_WAR,
                    'WEB-INF',
                    'lib',
                )
            )

        self.logger.info(_('Configuring Jasper Database resources'))

        with oreportsutil.XMLDoc(
            os.path.join(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_WAR,
                'WEB-INF',
                'js-jboss7-ds.xml',
            )
        ) as xml:
            for node in xml.xpath.xpathEval(
                '/datasources/datasource/driver'
            ):
                if 'postgresql' in node.content:
                    node.setContent('postgresql')

        self.logger.info(_('Customizing Jasper'))

        base = oreportscons.FileLocations.OVIRT_ENGINE_JASPER_CUSTOMIZATION
        for directory, dirs, files in os.walk(base):
            for f in files:
                shutil.copy2(
                    os.path.join(
                        directory,
                        f,
                    ),
                    os.path.join(
                        oreportscons.FileLocations.
                        OVIRT_ENGINE_REPORTS_JASPER_WAR,
                        os.path.relpath(
                            directory,
                            base,
                        ),
                    )
                )

        for p in sorted(
            (
                glob.glob(
                    os.path.join(
                        oreportscons.FileLocations.OVIRT_ENGINE_WAR_PATCHES,
                        self.environment[
                            oreportscons.JasperEnv.JASPER_NAME
                        ],
                        '*.patch',
                    )
                ) +
                glob.glob(
                    os.path.join(
                        oreportscons.FileLocations.OVIRT_ENGINE_WAR_PATCHES,
                        'common',
                        '*.patch',
                    )
                )
            ),
            key=lambda x: os.path.basename(x),
        ):
            rc, stdout, stderr = self.execute(
                args=(
                    self.command.get('patch'),
                    '-p1',
                    '-B', os.path.join(self._temproot, 'patches-backup'),
                    '-d', (
                        oreportscons.FileLocations.
                        OVIRT_ENGINE_REPORTS_JASPER_WAR
                    ),
                    '-i', p,
                    '--reject-file', '-',
                    '--batch',
                    '--silent',
                ),
            )

        self.logger.info(_('Customizing Jasper metadata'))

        everything = self._oreportsutil.jsexport(
            what='everything-post',
            args=(
                '--everything',
            ),
        )

        if self.environment[
            oreportscons.DBEnv.NEW_DATABASE
        ]:
            for f in (
                'users/anonymousUser.xml',
                'users/jasperadmin.xml',
                'users/organization_1/jasperadmin.xml',
            ):
                f = os.path.join(everything, f)
                if os.path.exists(f):
                    with oreportsutil.XMLDoc(f) as xml:
                        xml.setNodesContent(
                            '/user/enabled',
                            'false',
                        )

        for f in (
            'organizations/organizations.xml',
            'organizations/organization_1.xml',
        ):
            f = os.path.join(everything, f)
            if os.path.exists(f):
                with oreportsutil.XMLDoc(f) as xml:
                    xml.setNodesContent(
                        '/organization/theme',
                        self.environment[
                            oreportscons.JasperEnv.THEME
                        ],
                    )

        if (
            self.environment[oreportscons.JasperEnv.JASPER_NAME] == 'pro'
        ):
            self.logger.info(_('Customizing Jasper Pro Parts'))

            if self.environment[
                oreportscons.ConfigEnv.ADMIN_PASSWORD
            ] is not None:
                with oreportsutil.XMLDoc(
                    os.path.join(
                        everything,
                        'users',
                        'superuser.xml',
                    )
                ) as xml:
                    xml.setNodesContent(
                        '/user/password',
                        self.environment[
                            oreportscons.ConfigEnv.ADMIN_PASSWORD
                        ],
                    )

            if os.path.exists(
                os.path.join(
                    everything,
                    'resources',
                    'themes',
                    self.environment[
                        oreportscons.JasperEnv.THEME
                    ].replace(
                        '-',
                        '-002d'
                    ),
                ),
            ):
                shutil.rmtree(
                    os.path.join(
                        everything,
                        'resources',
                        'themes',
                        self.environment[
                            oreportscons.JasperEnv.THEME
                        ].replace(
                            '-',
                            '-002d'
                        ),
                    ),
                )

            shutil.copytree(
                os.path.join(
                    self.environment[oreportscons.JasperEnv.REPORTS_EXPORT],
                    'resources',
                    'themes',
                    self.environment[
                        oreportscons.JasperEnv.THEME
                    ].replace(
                        '-',
                        '-002d'
                    ),
                ),
                os.path.join(
                    everything,
                    'resources',
                    'themes',
                    self.environment[
                        oreportscons.JasperEnv.THEME
                    ].replace(
                        '-',
                        '-002d'
                    ),
                ),
            )

            with oreportsutil.XMLDoc(
                os.path.join(
                    everything,
                    'resources',
                    'themes',
                    '.folder.xml',
                )
            ) as xml:
                addNode = True
                for node in xml.xpath.xpathEval(
                    '/folder'
                ):
                    if self.environment[
                        oreportscons.JasperEnv.THEME
                    ] in node.content:
                        addNode = False
                if addNode:
                    addition = None
                    try:
                        addition = libxml2.parseDoc(
                            '''
                                <folder>%s</folder>
                            ''' % self.environment[
                                oreportscons.JasperEnv.THEME
                            ]
                        )
                        xml.xpath.xpathEval('/folder')[0].addChild(
                            addition.getRootElement()
                        )
                    finally:
                        # do not free, cause segmentation fault
                        # addition.freeDoc()
                        pass

        self._oreportsutil.jsimport(everything)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        after=(
            oreportscons.Stages.DB_SCHEMA,
            oreportscons.Stages.JASPER_DEPLOY_IMPORT,
        ),
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
    )
    def _artifacts(self):

        #
        # Remove embedded psql resources
        #
        for f in glob.glob(
            os.path.join(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_WAR,
                'WEB-INF',
                'lib',
                'postgresql-*.jar',
            )
        ):
            os.unlink(f)

        #
        # Files contain password
        #
        for f in (
            'WEB-INF/js-jboss7-ds.xml',
            'META-INF/context.xml',
        ):
            f = os.path.join(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_WAR,
                f
            )
            os.chown(
                f,
                osetuputil.getUid(
                    self.environment[osetupcons.SystemEnv.USER_ENGINE]
                ),
                osetuputil.getGid(
                    self.environment[osetupcons.SystemEnv.GROUP_ENGINE],
                ),
            )
            os.chmod(f, 0o600)

    @plugin.event(
        stage=plugin.Stages.STAGE_CLOSEUP,
    )
    def _closeup(self):
        for d in (
            self.environment[oreportscons.ConfigEnv.LEGACY_REPORTS_WAR],
            os.path.join(
                self.environment[oreportscons.ConfigEnv.JASPER_HOME],
                (
                    oreportscons.FileLocations.
                    LEGACY_OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
                ),
            ),
        ):
            if os.path.exists(d):
                self.logger.debug(_('Removing folder: %s'), d)
                shutil.rmtree(d)

    @plugin.event(
        stage=plugin.Stages.STAGE_CLEANUP,
    )
    def _cleanup(self):
        if self._temproot is not None and os.path.exists(self._temproot):
            shutil.rmtree(self._temproot)


# vim: expandtab tabstop=4 shiftwidth=4
