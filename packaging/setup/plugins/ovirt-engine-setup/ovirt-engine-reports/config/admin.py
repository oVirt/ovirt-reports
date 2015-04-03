#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2013-2015 Red Hat, Inc.
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


import gettext


from otopi import constants as otopicons
from otopi import plugin
from otopi import util


from ovirt_engine_setup import constants as osetupcons
from ovirt_engine_setup import dialog


from ovirt_engine_setup.reports import constants as oreportscons


def _(m):
    return gettext.dgettext(message=m, domain='ovirt-engine-reports')


@util.export
class Plugin(plugin.PluginBase):

    def __init__(self, context):
        super(Plugin, self).__init__(context=context)

    @plugin.event(
        stage=plugin.Stages.STAGE_BOOT,
    )
    def _boot(self):
        self.environment[
            otopicons.CoreEnv.LOG_FILTER_KEYS
        ].append(
            oreportscons.ConfigEnv.ADMIN_PASSWORD
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_INIT,
    )
    def _init(self):
        self.environment.setdefault(
            oreportscons.ConfigEnv.ADMIN_PASSWORD,
            None
        )

    @plugin.event(
        stage=plugin.Stages.STAGE_CUSTOMIZATION,
        condition=lambda self: (
            self.environment[
                oreportscons.CoreEnv.ENABLE
            ] and
            self.environment[
                oreportscons.DBEnv.NEW_DATABASE
            ]
        ),
        before=(
            osetupcons.Stages.DIALOG_TITLES_E_MISC,
        ),
        after=(
            osetupcons.Stages.DIALOG_TITLES_S_MISC,
        ),
    )
    def _customization(self):
        if self.environment[
            oreportscons.ConfigEnv.ADMIN_PASSWORD
        ] is None:
            valid = False
            password = None
            while not valid:
                password = self.dialog.queryString(
                    name='OVESETUP_REPORTS_CONFIG_JASPER_ADMIN_PASSWORD',
                    note=_('Reports power users password: '),
                    prompt=True,
                    hidden=True,
                )
                password2 = self.dialog.queryString(
                    name='OVESETUP_REPOTS_CONFIG_JASPER_ADMIN_PASSWORD',
                    note=_('Confirm Reports power users password: '),
                    prompt=True,
                    hidden=True,
                )

                if password != password2:
                    self.logger.warning(_('Passwords do not match'))
                else:
                    try:
                        import cracklib
                        cracklib.FascistCheck(password)
                        valid = True
                    except ImportError:
                        # do not force this optional feature
                        self.logger.debug(
                            'cannot import cracklib',
                            exc_info=True,
                        )
                        valid = True
                    except ValueError as e:
                        self.logger.warning(
                            _('Password is weak: {error}').format(
                                error=e,
                            )
                        )
                        valid = dialog.queryBoolean(
                            dialog=self.dialog,
                            name=(
                                'OVESETUP_REPORTS_CONFIG_WEAK_JASPER_PASSWORD'
                            ),
                            note=_(
                                'Use weak password? '
                                '(@VALUES@) [@DEFAULT@]: '
                            ),
                            prompt=True,
                            default=False,
                        )

            self.environment[oreportscons.ConfigEnv.ADMIN_PASSWORD] = password


# vim: expandtab tabstop=4 shiftwidth=4
