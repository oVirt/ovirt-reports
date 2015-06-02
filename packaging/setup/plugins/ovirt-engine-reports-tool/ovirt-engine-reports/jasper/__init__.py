#
# ovirt-engine-setup -- ovirt engine setup
# Copyright (C) 2015 Red Hat, Inc.
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


"""Reports setup core plugin."""


from otopi import util


from . import change_admin_password
from . import export_saved_reports
from . import import_saved_reports


@util.export
def createPlugins(context):
    change_admin_password.Plugin(context=context)
    export_saved_reports.Plugin(context=context)
    import_saved_reports.Plugin(context=context)


# vim: expandtab tabstop=4 shiftwidth=4
