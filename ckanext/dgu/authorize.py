from logging import getLogger

from pylons.i18n import _
from ckan.logic.auth import get_package_object
import ckan.logic.auth
import ckan.new_authz as new_authz
from ckanext.dgu.lib import helpers as dgu_helpers

log = getLogger(__name__)

def dgu_package_update(context, data_dict):
    model = context['model']
    user = context.get('user')
    user_obj = model.User.get( user )
    package = get_package_object(context, data_dict)

    # Allow sysadmins to edit anything
    # This includes UKLP harvested datasets.
    #   Note: the harvest user *is* a sysadmin
    #   Note: if changing this, check the code and comments in
    #         ckanext/forms/dataset_form.py:DatasetForm.form_to_db_schema_options()
    if user_obj.sysadmin:
        return {'success': True}

    # UKLP datasets and other harvested datasets cannot be edited by the
    # average admin/editor because changes will be overwritten on next harvest.
    if dgu_helpers.was_dataset_harvested(package.extras):
        return {'success': False,
                'msg': _('User %s not authorized to edit harvested datasets') % str(user)}

    # Leave the core CKAN auth to work out the hierarchy stuff
    return ckan.logic.auth.update.package_update(context, data_dict)

def dgu_dataset_delete(context, data_dict):
    """
    Determines whether a dataset's state can be set to "deleted".

    Currently only sysadmin users can do this, apart from UKLP.
    """
    model = context['model']
    user = context.get('user')
    if not user:
        return {'success': False}
    user_obj = model.User.get(user)
    package = get_package_object(context, data_dict)

    # Sysadmin can delete any package, including UKLP
    if user_obj.sysadmin:
        return {'success': True}

    # Don't allow admin/editor to delete
    # * apart from UKLP datasets which CAN be withdrawn by the appropriate
    # admin/editor because they are all live services, so can't be cached to
    # preserve them without the service provider's help
    if package.extras.get('UKLP', '') != 'True':
        return {'success': False}

    # Leave the core CKAN auth to work out the hierarchy stuff
    return ckan.logic.auth.delete.package_delete(context, data_dict)

def dgu_extra_fields_editable(context, data_dict):
    """
    Determines whether a dataset's extra-fields are editable directly.

    Typically, this is only something we want sysadmins to be able to do.
    """
    user = context.get('user')
    if dgu_helpers.is_sysadmin_by_context(context):
        return {'success': True}
    else:
        return {'success': False,
                'msg': _('User %s not authorized to edit a dataset\'s extra fields') % str(user)}

def dgu_user_show(context, data_dict):
    user_id = context.get('user','')
    viewing_id = data_dict['id']

    if viewing_id == user_id:
        return {'success': True}

    return dgu_user_list(context, data_dict)

def dgu_user_list(context, data_dict):
    model = context['model']
    user = context.get('user','')
    user_obj = model.User.get(user)

    if dgu_helpers.is_sysadmin_by_context(context):
        return {'success': True}

    if not user or not user_obj:
        return {'success': False, 'msg': _('You must be logged in to view the user list')}

    if not len(user_obj.get_groups('organization')):
        return { 'success': False, 'msg': _('Only publishers may view this page') }

    return {'success': True}

def dgu_feedback_create(context, data_dict):
    model = context['model']
    user = context.get('user','')

    if not user:
        return {'success': False, 'msg': _('Only logged in users can post feedback')}

    return { 'success': True }

def dgu_feedback_update(context, data_dict):
    """
    Checks whether the user has permission to update the feedback.
    """
    user = context.get('user','')

    if not user:
        return {'success': False, 'msg': _('Only logged in admins can update feedback')}

    # Sysadmins only
    return { 'success': False, 'msg': _('Only sysadmins can update feedback') }


def dgu_feedback_delete(context, data_dict):
    """
    Determines whether the current user has the ability to flip the active flag
    on the feedback item.  For now, this is the same as update.
    """
    return dgu_feedback_update(context, data_dict)

def dgu_organization_delete(context, data_dict):
    # Sysadmins only
    return { 'success': False, 'msg': _('Only sysadmins can delete publishers') }

def dgu_group_change_state(context, data_dict):
    return dgu_organization_delete(context, data_dict)

def dgu_group_update(context, data_dict):
    user = context.get('user', '')

    if not user:
        return {'success': False, 'msg': _('Must be logged in')}

    group = ckan.logic.auth.get_group_object(context, data_dict)
    authorized = new_authz.has_user_permission_for_group_or_org(group.id, user, 'manage_group')

    if authorized:
        return { 'success': True }

    roles = dgu_helpers.get_user_drupal_roles(user)
    if ('moderator' in roles) or ('administrator' in roles):
        return { 'success': True }
    else:
        return { 'success': False, 'msg': _('Not authed')}

def dgu_group_user_update(context, data_dict):
    user = context.get('user', '')

    if not user:
        return {'success': False, 'msg': _('Must be logged in')}

    group = ckan.logic.auth.get_group_object(context, data_dict)
    authorized = new_authz.has_user_permission_for_group_or_org(group.id, user, 'admin')

    if authorized:
        return { 'success': True }

    roles = dgu_helpers.get_user_drupal_roles(user)
    if ('moderator' in roles) or ('administrator' in roles):
        return { 'success': True }
    else:
        return { 'success': False, 'msg': _('Not authed')}
