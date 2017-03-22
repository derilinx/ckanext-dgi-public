"""
navl validators for the DGU package schema.
"""
import codecs
import os
import simplejson as json
from itertools import chain, groupby
from pylons.i18n import _
from ckan.lib.navl.dictization_functions import unflatten, Invalid, \
                                                StopOnError, missing
from ckanext.dgu.lib.helpers import resource_type as categorise_resource


def allow_empty_if_inventory(key, data, errors, context):
    """ Allow a specific field to not be required if unpublished=true """
    unpublished = data.get('unpublished', False)
    value = data.get(key)

    if unpublished:
        if value is missing or value is None:
            data.pop(key, None)
            raise StopOnError
    else:
        if not value or value is missing:
            errors[key].append(_('Missing value'))
            raise StopOnError



def required_if_inventory(key, data, errors, context):
    """ Make a field required if inventory=true in extras """
    pass

def drop_if_same_as_publisher(key, data, errors, context):
    """
    Validates the contact- and foi- data.

    If it's the same as that on the publisher, then the data is dropped,
    otherwise it's kept, and stored on the dataset (as an extra field).

    For example:

    if key == 'contact-name'.  Then we load the group referenced
    by 'groups__0__name', and then check group.extras['contact-name'].
    """
    from ckan.model.group import Group
    field_name = key[0] # extract from tuple

    group_ref = None
    for ref_name in ['name', 'id']:
        group_ref = data.get(('groups', 0, ref_name), None)
        if group_ref and group_ref is not missing:
            break

    if not group_ref:
        return

    group = Group.get(group_ref)
    if not group:
        return

    if group.extras.get(field_name, None) == data[key]:
        # Remove from data and errors iff the two are equal.
        # If the group doesn't have an extra field for this key,
        # then store it against the dataset.
        data.pop(key, None)
        errors.pop(key, None)
        raise StopOnError

def populate_from_publisher_if_missing(key, data, errors, context):
    """
    If the data is missing, then populate from the publisher.
    """
    from ckan.model.group import Group

    if data[key] is not missing:
        return

    field_name = key[0] # extract from tuple
    group = Group.get(data.get(('groups', 0, 'name'), None))
    if not group:
        return
    data[key] = group.extras.get(field_name, None)

def validate_language(key, data, errors, context):
    """
    Munges language option. Should be ISO 639 but will also take plaintext
    English, Irish, Gaeilge and convert
    """
    lang = str(data[('language',)]).lower()
    #TODO should probably validate these to make sure they're actual codes?

    if not lang:
        #assume english
        data[('language',)] = "eng"
    elif (len(lang) > 4):
        #not an ISO 639 code
        if (lang == "english"):
            data[('language',)] = "eng"
        elif (lang == "irish" or lang == "gaeilge"):
            data[('language',)] = "gle"
        else:
            errors[('language',)] = ['Language must be an ISO-639 code, "English", "Irish", or "Gaeilge"']
            raise StopOnError
    else:
        data[('language',)] = lang

def validate_license(key, data, errors, context):
    """
    Validates the selected license options.

    Validation rules must be true to validate:

     license_id == ''                             => access_constraints != ''
     license_id != '__extra__' ^ license_id != '' => access_constraints == ''

    Additional transformations occur:

     license_id == '__extra__' => licence_id := None
     access_constraints != ''    => license_id := access_constraints
     access_constraints is DROPPED

    """


    #DGI: We actually don't need this, and I don't like what it does to access_constraints,
    #so let's just not call this.

    if data[('license_id',)]== '__extra__': # harvested dataset
        data[('license_id',)] = None
        return

    license_id = bool(data[('license_id',)])
    license_id_other = bool(data.get(('access_constraints',)))

    if not (license_id ^ license_id_other):
        if license_id:
            # i.e. both license_id and access_constraints filled in
            errors[('license_id',)] = ['Leave the "Access Constraints" box empty if '
                                       'selecting a license from the list']
        else:
            # i.e. neither license_id nor access_constraints filled in
            errors[('license_id',)] = ['Please enter the access constraints.']
        #return

    if not license_id:
        data[('license_id',)] = data[('access_constraints',)]
    if license_id_other:
        del data[('access_constraints',)]
    del errors[('access_constraints',)]

def validate_resources(key, data, errors, context):
    """
    Validates that the timeseries_resources and individual_resources.

    At most one of them should contain resources.
    """
    timeseries_resources = _extract_resources('timeseries', data)
    individual_resources = _extract_resources('individual', data)

    if len(timeseries_resources) and len(individual_resources):
        errors[('validate_resources',)] = ['Only define timeseries or individual '
                                               'resources, not both']

def merge_resources(key, data, errors, context):
    """
    Merges additional resources and data resources into a single entry in the data dict.

    And removes the '{additional,timeseries,individual}_resources' entries.

    This post-processing only occurs if there have been no validation errors.
    This prevents us losing the user's input.
    """
    if key != ('__after',):
        raise Exception('The merge_resources function should only be '
                        'called as a post-processing function.  '
                        'Called with "%s"' % key)

    for value in errors.values():
        if value:
            return

    _merge_dict(data)
    _merge_dict(errors)

def _merge_dict(d):
    """
    Helper function that performs a resource merge on the given dict.

    A resource merge takes a flattened dictionary, with keys (tuples) of the
    form `('additional_resource', 0, 'url')` and `('timeseries_resource', 0, 'url')`.
    And transforms it into a dict with the above keys merged into ones of the
    form `('resources', 0, 'url')`.

    d is the dict to perform the merge on.
    """
    additional_resources = _extract_resources('additional', d)
    timeseries_resources = _extract_resources('timeseries', d)
    individual_resources = _extract_resources('individual', d)
    resources = sorted(chain(additional_resources,
                             timeseries_resources,
                             individual_resources))

    # group by the first two items in the flattened key
    #  - num : from enumerate.
    #  - resource : key we've grouped on, e.g. ('additional_resource', 0)
    #  - values : iterator over the resource keys,, e.g.
    #             [ ('additional_resource', 0, 'url'),
    #               ('additional_resource', 0, 'description') ]
    for (num, (resource, values)) in enumerate(groupby(resources, lambda t: t[:2])):
        resource_type, original_index = resource
        for (_,_,field) in values:
            d[('resources', num, field)] = d[(resource_type, original_index, field)]

            # delete the original key from the d, e.g.
            del d[(resource_type, original_index, field)]

def unmerge_resources(key, data, errors, context):
    """
    Splits the merged resources back into their respective resource types.

    And removes the 'resources' entry.

    This post-processing only occurs if there have been no validation errors.
    """
    if key != ('__after',):
        raise Exception('The unmerge_resources function should only be '
                        'called as a post-processing function.  '
                        'Called with "%s"' % key)

    for value in errors.values():
        if value:
            return

    # data[('resources', '0', 'url')]

    # Categorise each resource, and add it to the respective entry
    unflattened_resources = unflatten(data).get('resources', [])
    error_resources = unflatten(errors).get('resources', [])
    resources = zip(unflattened_resources,
                    map(categorise_resource, unflattened_resources),
                    error_resources)

    for resource_type in ('additional', 'timeseries', 'individual'):
        match = lambda (r,t,e): t == resource_type # match resources of this resource_type
        for index, (resource,_,error_resource) in enumerate(filter(match, resources)):
            for field in resource.keys():
                data_key = ('%s_resources'%resource_type, index, field)
                data[data_key] = resource[field]
            for field in error_resource.keys():
                error_key = ('%s_resources'%resource_type, index, field)
                errors[error_key] = []

    for key in ( key for key in errors.keys() if key[0] == 'resources' ):
        del errors[key]

def _validate_resource_types(allowed_types, default=None):
    """
    Returns a function that validates the given resource_type is allowed.

    If a resource_type is False-like, then it returns a default value when
    available.
    """

    def _converter(value):
        if not value and default:
            return default
        elif value not in allowed_types:
            raise Invalid(_('Invalid resource type: %s' % value))
        return value
    return _converter

validate_additional_resource_types = _validate_resource_types(
                                         ('documentation',),
                                         default='documentation')

validate_data_resource_types = _validate_resource_types(
                                   ('api','file'),
                                   default='file')

def _extract_resources(name, data):
    """
    Extracts the flattened resources with the given name from the flattened data dict
    """
    return [ key for key in data.keys() if key[0] == name+'_resources' ]

def remove_blank_resources(key, data, errors, context):
    '''
    If the user leaves values for a resource blank, then remove it plus any
    validation errors.
    '''
    assert key == ('__after',)
    # needs to be run after resource validation so it can delete validation
    # errors blank resources

    additional_resources = _extract_resources('additional', data)
    timeseries_resources = _extract_resources('timeseries', data)
    individual_resources = _extract_resources('individual', data)
    resources = sorted(chain(additional_resources,
                             timeseries_resources,
                             individual_resources))

    user_filled_fields = set(('description', 'format', 'url', 'date'))

    for (resource, values_iter) in groupby(resources, lambda t: t[:2]):
        resource_type, original_index = resource
        is_blank_resource = True
        values = list(values_iter) # copy it - we need it twice
        for (_,_,field) in values:
            if field not in user_filled_fields:
                continue
            field_value = data[(resource_type, original_index, field)]
            if field_value.strip() if isinstance(field_value, basestring) else field_value:
                is_blank_resource = False
                break
        if is_blank_resource:
            for (_,_,field) in values:
                triple = (resource_type, original_index, field)
                del data[triple]
                if triple in errors:
                    del errors[triple]


themes_filepath = os.path.abspath(os.path.join(__file__, '../../themes.json'))
if not os.path.exists(themes_filepath):
    raise IOError(2, 'Unable to read themes.json')
with codecs.open(themes_filepath, encoding='utf8') as fp:
    themes_json = fp.read()
    themes_list = json.loads(themes_json)

def validate_theme(key, data, errors, context):
    """
    Validates theme-primary to make sure it's a valid theme.
    """
    theme = data[('theme-primary',)]
    for theme_dict in themes_list:
        nameStored = theme_dict.get('stored_as', False)
        nameTitle = theme_dict.get('title', False)
        if theme == nameStored or theme == nameTitle:
            return
    #if it made it here, we don't have it
    errors[('theme-primary',)] = ['theme-primary is not valid.']
