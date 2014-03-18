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


"""Connection plugin."""


import socket
import gettext
_ = lambda m: gettext.dgettext(message=m, domain='ovirt-engine-reports')


from otopi import constants as otopicons
from otopi import transaction
from otopi import util
from otopi import plugin


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import reportsconstants as oreportscons
from ovirt_engine_setup import database
from ovirt_engine_setup import dialog
from ovirt_engine_setup import util as osetuputil


@util.export
class Plugin(plugin.PluginBase):
    """Connection plugin."""

    class DBTransaction(transaction.TransactionElement):
        """yum transaction element."""

        def __init__(self, parent):
            self._parent = parent

        def __str__(self):
            return _("Reports database Transaction")

        def prepare(self):
            pass

        def abort(self):
            connection = self._parent.environment[
                oreportscons.DBEnv.CONNECTION
            ]
            if connection is not None:
                connection.rollback()
                self._parent.environment[oreportscons.DBEnv.CONNECTION] = None

        def commit(self):
            connection = self._parent.environment[
                oreportscons.DBEnv.CONNECTION
            ]
            if connection is not None:
                connection.commit()

    def _checkDbEncoding(self, environment):

        statement = database.Statement(
            environment=environment,
            dbenvkeys=oreportscons.Const.REPORTS_DB_ENV_KEYS,
        )
        encoding = statement.execute(
            statement="""
                show server_encoding
            """,
            ownConnection=True,
            transaction=False,
        )[0]['server_encoding']
        if encoding.lower() != 'utf8':
            raise RuntimeError(
                _(
                    'Encoding of the Reports database is {encoding}. '
                    'Engine installation is only supported on servers '
                    'with default encoding set to UTF8. Please fix the '
                    'default DB encoding before you continue'
                ).format(
                    encoding=encoding,
                )
            )

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_SETUP,
    )
    def _setup(self):
        self.environment[otopicons.CoreEnv.MAIN_TRANSACTION].append(
            self.DBTransaction(self)
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        name=oreportscons.Stages.DB_CONNECTION_CUSTOMIZATION,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_DATABASE,
        ),
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_DATABASE,
        ),
    )
    def _customization(self):
        dbovirtutils = database.OvirtUtils(
            plugin=self,
            dbenvkeys=oreportscons.Const.REPORTS_DB_ENV_KEYS,
        )

        interactive = None in (
            self.environment[oreportscons.DBEnv.HOST],
            self.environment[oreportscons.DBEnv.PORT],
            self.environment[oreportscons.DBEnv.DATABASE],
            self.environment[oreportscons.DBEnv.USER],
            self.environment[oreportscons.DBEnv.PASSWORD],
        )

        if interactive:
            self.dialog.note(
                text=_(
                    "\n"
                    "ATTENTION\n"
                    "\n"
                    "Manual action required.\n"
                    "Please create database for ovirt-engine use. "
                    "Use the following commands as an example:\n"
                    "\n"
                    "create role {user} with login encrypted password '{user}'"
                    ";\n"
                    "create database {database} owner {user}\n"
                    " template template0\n"
                    " encoding 'UTF8' lc_collate 'en_US.UTF-8'\n"
                    " lc_ctype 'en_US.UTF-8';\n"
                    "\n"
                    "Make sure that database can be accessed remotely.\n"
                    "\n"
                ).format(
                    user=oreportscons.Defaults.DEFAULT_DB_USER,
                    database=oreportscons.Defaults.DEFAULT_DB_DATABASE,
                ),
            )

        connectionValid = False
        while not connectionValid:
            host = self.environment[oreportscons.DBEnv.HOST]
            port = self.environment[oreportscons.DBEnv.PORT]
            secured = self.environment[oreportscons.DBEnv.SECURED]
            securedHostValidation = self.environment[
                oreportscons.DBEnv.SECURED_HOST_VALIDATION
            ]
            db = self.environment[oreportscons.DBEnv.DATABASE]
            user = self.environment[oreportscons.DBEnv.USER]
            password = self.environment[oreportscons.DBEnv.PASSWORD]

            if host is None:
                while True:
                    host = self.dialog.queryString(
                        name='OVESETUP_REPORTS_DB_HOST',
                        note=_('Reports database host [@DEFAULT@]: '),
                        prompt=True,
                        default=oreportscons.Defaults.DEFAULT_DB_HOST,
                    )
                    try:
                        socket.getaddrinfo(host, None)
                        break  # do while missing in python
                    except socket.error as e:
                        self.logger.error(
                            _('Host is invalid: {error}').format(
                                error=e.strerror
                            )
                        )

            if port is None:
                while True:
                    try:
                        port = osetuputil.parsePort(
                            self.dialog.queryString(
                                name='OVESETUP_REPORTS_DB_PORT',
                                note=_('Reports database port [@DEFAULT@]: '),
                                prompt=True,
                                default=oreportscons.Defaults.DEFAULT_DB_PORT,
                            )
                        )
                        break  # do while missing in python
                    except ValueError:
                        pass

            if secured is None:
                secured = dialog.queryBoolean(
                    dialog=self.dialog,
                    name='OVESETUP_REPORTS_DB_SECURED',
                    note=_(
                        'Reports database secured connection (@VALUES@) '
                        '[@DEFAULT@]: '
                    ),
                    prompt=True,
                    default=oreportscons.Defaults.DEFAULT_DB_SECURED,
                )

            if not secured:
                securedHostValidation = False

            if securedHostValidation is None:
                securedHostValidation = dialog.queryBoolean(
                    dialog=self.dialog,
                    name='OVESETUP_REPORTS_DB_SECURED_HOST_VALIDATION',
                    note=_(
                        'Reports database host name validation in secured '
                        'connection (@VALUES@) [@DEFAULT@]: '
                    ),
                    prompt=True,
                    default=True,
                ) == 'yes'

            if db is None:
                db = self.dialog.queryString(
                    name='OVESETUP_REPORTS_DB_DATABASE',
                    note=_('Reports database name [@DEFAULT@]: '),
                    prompt=True,
                    default=oreportscons.Defaults.DEFAULT_DB_DATABASE,
                )

            if user is None:
                user = self.dialog.queryString(
                    name='OVESETUP_REPORTS_DB_USER',
                    note=_('Reports database user [@DEFAULT@]: '),
                    prompt=True,
                    default=oreportscons.Defaults.DEFAULT_DB_USER,
                )

            if password is None:
                password = self.dialog.queryString(
                    name='OVESETUP_REPORTS_DB_PASSWORD',
                    note=_('Reports database password: '),
                    prompt=True,
                    hidden=True,
                )

            dbenv = {
                oreportscons.DBEnv.HOST: host,
                oreportscons.DBEnv.PORT: port,
                oreportscons.DBEnv.SECURED: secured,
                oreportscons.DBEnv.SECURED_HOST_VALIDATION: (
                    securedHostValidation
                ),
                oreportscons.DBEnv.USER: user,
                oreportscons.DBEnv.PASSWORD: password,
                oreportscons.DBEnv.DATABASE: db,
            }

            if interactive:
                try:
                    dbovirtutils.tryDatabaseConnect(dbenv)
                    self._checkDbEncoding(dbenv)
                    self.environment.update(dbenv)
                    connectionValid = True
                except RuntimeError as e:
                    self.logger.error(
                        _(
                            'Cannot connect to Reports '
                            'database: {error}'
                        ).format(
                            error=e,
                        )
                    )
            else:
                # this is usally reached in provisioning
                # or if full ansewr file
                self.environment.update(dbenv)
                connectionValid = True

        try:
            self.environment[
                oreportscons.DBEnv.NEW_DATABASE
            ] = dbovirtutils.isNewDatabase()
        except:
            self.logger.debug('database connection failed', exc_info=True)

    @plugin.event(
        stage=plugin.Stages.STAGE_MISC,
        name=oreportscons.Stages.DB_CONNECTION_AVAILABLE,
        condition=lambda self: self.environment[oreportscons.CoreEnv.ENABLE],
        after=(
            oreportscons.Stages.DB_SCHEMA,
        ),
    )
    def _connection(self):
        self.environment[
            oreportscons.DBEnv.STATEMENT
        ] = database.Statement(
            environment=self.environment,
            dbenvkeys=oreportscons.Const.REPORTS_DB_ENV_KEYS,
        )
        # must be here as we do not have database at validation
        self.environment[
            oreportscons.DBEnv.CONNECTION
        ] = self.environment[oreportscons.DBEnv.STATEMENT].connect()


# vim: expandtab tabstop=4 shiftwidth=4
