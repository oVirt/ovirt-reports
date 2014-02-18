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
from otopi import base
from otopi import util
from otopi import plugin
from otopi import transaction


from ovirt_engine import util as outil


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import reportsconstants as oreportscons
from ovirt_engine_setup import util as osetuputil
from ovirt_engine_setup import database


@util.export
class Plugin(plugin.PluginBase):
    """Schema plugin."""

    class XMLDoc(base.Base):

        @property
        def document(self):
            return self._doc

        @property
        def xpath(self):
            return self._ctx

        def __init__(self, f):
            super(Plugin.XMLDoc, self).__init__()
            self._file = f
            self._doc = None
            self._ctx = None

        def __enter__(self):
            self._doc = libxml2.parseFile(self._file)
            self._ctx = self._doc.xpathNewContext()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            if not exc_type:
                with open(self._file, 'w') as f:
                    f.write(
                        self._doc.serialize(
                            'UTF-8',
                            libxml2.XML_SAVE_FORMAT,
                        )
                    )
                os.chmod(self._file, 0o644)

            if self._doc:
                self._doc.freeDoc()
                self._doc = None
            if self._ctx:
                self._ctx.xpathFreeContext()
                self._ctx = None

        def setNodesContent(self, path, content):
            for node in self.xpath.xpathEval(path):
                node.setContent(content)

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
                if os.path.exists(entry['dst']):
                    shutil.rmtree(entry['dst'])

    def _buildJs(self, cmd, config):
        try:
            myumask = os.umask(0o022)

            rc, stdout, stderr = self.execute(
                args=(
                    './js-ant',
                    '-DmasterPropsSource=%s' % config,
                    cmd
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

    def _exportJs(self, what, args):
        dest = os.path.join(
            self._temproot,
            what,
        )
        self.execute(
            args=(
                './js-export.sh',
                '--output-dir', dest,
            ) + args,
            cwd=os.path.join(
                self.environment[
                    oreportscons.ConfigEnv.JASPER_HOME
                ],
                'buildomatic',
            ),
            envAppend={
                'JAVA_HOME': self.environment[
                    osetupcons.ConfigEnv.JAVA_HOME
                ],
                'JAVA_OPTS': '-Djava.io.tmpdir=%s' % self._javatmp,
                'ADDITIONAL_CONFIG_DIR': (
                    oreportscons.FileLocations.
                    OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
                ),
            },
        )
        return dest

    def _importJs(self, src):
        self.execute(
            args=(
                './js-import.sh',
                '--input-dir', src,
                '--update',
            ),
            cwd=os.path.join(
                self.environment[
                    oreportscons.ConfigEnv.JASPER_HOME
                ],
                'buildomatic',
            ),
            envAppend={
                'JAVA_HOME': self.environment[
                    osetupcons.ConfigEnv.JAVA_HOME
                ],
                'JAVA_OPTS': '-Djava.io.tmpdir=%s' % self._javatmp,
                'ADDITIONAL_CONFIG_DIR': (
                    oreportscons.FileLocations.
                    OVIRT_ENGINE_REPORTS_BUILDOMATIC_CONFIG
                ),
            },
        )

    def _workaroundUsersNullPaswords(self, src):
        for f in glob.glob(os.path.join(src, 'users', '*.xml')):
            with self.XMLDoc(f) as xml:
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
                        '@PACKAGE_NAME@': oreportscons.Const.PACKAGE_NAME,
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
            oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_EXPORT,
            reportsImport,
            symlinks=True,
        )

        if self.environment[oreportscons.ConfigEnv.ADMIN_PASSWORD] is not None:
            with self.XMLDoc(
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
            'resources/reports_resources/JDBC/data_sources/ovirt.xml',
        )
        if self._dwhdatasource:
            shutil.copyfile(
                self._dwhdatasource,
                dwhdatasource,
            )
        else:
            with self.XMLDoc(dwhdatasource) as xml:
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
        self._temproot = None
        self._quartzprops = None
        self._users = None
        self._jobs = None
        self._dwhdatasource = None
        self._savedReports = None

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self._temproot = tempfile.mkdtemp()
        self._javatmp = os.path.join(self._temproot, 'tmp')
        os.mkdir(self._javatmp)

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
        condition=lambda self: (
            self.environment[oreportscons.CoreEnv.ENABLE] and
            not self.environment[oreportscons.DBEnv.NEW_DATABASE]
        ),
        before=(
            oreportscons.Stages.DB_SCHEMA,
        ),
    )
    def _export(self):
        config = self._jasperConfiguration()

        self.logger.info(_('Exporting data out of Jasper'))
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
                oreportscons.FileLocations.
                LEGACY_OVIRT_ENGINE_REPORTS_JASPER_WAR
            )
        ):
            shutil.copyfile(
                (
                    oreportscons.FileLocations.
                    LEGACY_OVIRT_ENGINE_REPORTS_JASPER_QUARTZ
                ),
                self._quartzprops,
            )

            self.logger.info(
                _("Regenerating Jasper's build configuration files")
            )

            self._buildJs(config=config, cmd='gen-config')
        else:
            raise RuntimeError(
                _('Could not detect Jasper war folder')
            )

        everything = self._exportJs(
            what='everything',
            args=(
                '--everything',
            ),
        )
        if os.path.exists(
            os.path.join(
                everything,
                'resources/saved_reports',
            )
        ):
            self._savedReports = self._exportJs(
                what='savedReports',
                args=(
                    '--uris', '/saved_reports',
                ),
            )
        self._jobs = self._exportJs(
            what='jobs',
            args=(
                '--report-jobs', '/',
            ),
        )
        self._users = self._exportJs(
            what='users',
            args=(
                '--users',
                '--roles',
            ),
        )
        dwhdatasourceexport = self._exportJs(
            what='dwhdatasourceexport',
            args=(
                '--uris', '/reports_resources/JDBC/data_sources/ovirt',
            ),
        )
        self._dwhdatasource = os.path.join(
            dwhdatasourceexport,
            'resources/reports_resources/JDBC/data_sources/ovirt.xml',
        )

        self._workaroundUsersNullPaswords(self._users)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.DB_SCHEMA,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
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
            'init-js-db-ce',
            'import-minimal-ce',
            'deploy-webapp-ce',
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
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            oreportscons.Stages.DB_SCHEMA,
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
            self._importJs(self._users)

        if self._savedReports:
            self._importJs(self._savedReports)

        self._importJs(self._prepareOvirtReports())

        #
        # We import users twice because we need permissions to be
        # preserved as well as users passwords reset after importing
        # reports in previous step.
        #
        if self._users:
            self._importJs(self._users)

        if self._jobs:
            self._importJs(self._jobs)

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

        for f in glob.glob(
            os.path.join(
                oreportscons.FileLocations.OVIRT_ENGINE_REPORTS_JASPER_WAR,
                'WEB-INF',
                'lib',
                'postgresql-*.jar',
            )
        ):
            os.unlink(f)

        with self.XMLDoc(
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

        for p in sorted(
            glob.glob(
                os.path.join(
                    oreportscons.FileLocations.OVIRT_ENGINE_WAR_PATCHES,
                    '*.patch',
                )
            )
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

        self.logger.info(_('Customizing Jasper metadata'))

        everything = self._exportJs(
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
            ):
                with self.XMLDoc(
                    os.path.join(
                        everything,
                        f,
                    ),
                ) as xml:
                    xml.setNodesContent(
                        '/user/enabled',
                        'false',
                    )

        with self.XMLDoc(
            os.path.join(
                everything,
                'organizations',
                'organizations.xml',
            ),
        ) as xml:
            xml.setNodesContent(
                '/organization/theme',
                'ovirt-reports-theme',
            )

        self._importJs(everything)

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
            oreportscons.FileLocations.LEGACY_OVIRT_ENGINE_REPORTS_JASPER_WAR,
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
