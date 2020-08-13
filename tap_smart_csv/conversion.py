import dateutil
import pytz
import singer

LOGGER = singer.get_logger()


def convert_row(row, schema):
    to_return = {}
    for key, value in row.items():
        field_schema = schema['properties'][key]
        declared_types = field_schema.get('type', 'string')

        LOGGER.debug('Converting {} value {} to {}'.format(key, value, declared_types))
        coerced = coerce(value, declared_types)
        to_return[key] = coerced

    return to_return

def coerce(datum,declared_types):
    if datum is None or datum == '':
        return None

    desired_type = "string"
    if isinstance(declared_types, list):
        if None in declared_types:
            declared_types.remove(None)
        desired_type = declared_types.pop()

    coerced, _ = convert(datum, desired_type)
    return coerced


def convert(datum, desired_type=None):
    """
    Returns tuple of (converted_data_point, json_schema_type,).
    """
    if datum is None or datum == '':
        return None, None,

    if desired_type in (None, 'integer'):
        try:
            to_return = int(datum)  # Confirm it can be coerced to int
            if not datum.lstrip("-+").isdigit():
                raise TypeError
            return to_return, 'integer',
        except (ValueError, TypeError):
            pass

    if desired_type in (None, 'number'):
        try:
            to_return = float(datum)
            return to_return, 'number',
        except (ValueError, TypeError):
            pass

    if desired_type == 'date-time':
        try:
            to_return = dateutil.parser.parse(datum)

            if (to_return.tzinfo is None or
                    to_return.tzinfo.utcoffset(to_return) is None):
                to_return = to_return.replace(tzinfo=pytz.utc)

            return to_return.isoformat(), 'date-time',
        except (ValueError, TypeError):
            pass

    return str(datum), 'string',


def count_sample(sample, start=None):
    if start is None:
        start = {}

    for key, value in sample.items():
        if key not in start:
            start[key] = {}

        (_, datatype) = convert(value)
        if datatype is not None:
            start[key][datatype] = start[key].get(datatype, 0) + 1

    return start


def count_samples(samples):
    to_return = {}

    for sample in samples:
        to_return = count_sample(sample, to_return)

    return to_return


def pick_datatype(counts):
    """
    If the underlying records are ONLY of type `integer`, `number`,
    or `date-time`, then return that datatype.

    If the underlying records are of type `integer` and `number` only,
    return `number`.

    Otherwise return `string`.
    """
    to_return = 'string'

    if len(counts) == 1:
        if counts.get('integer', 0) > 0:
            to_return = 'integer'
        elif counts.get('number', 0) > 0:
            to_return = 'number'

    elif (len(counts) == 2 and
          counts.get('integer', 0) > 0 and
          counts.get('number', 0) > 0):
        to_return = 'number'

    return to_return


def generate_schema(samples):
    to_return = {}
    counts = count_samples(samples)

    for key, value in counts.items():
        datatype = pick_datatype(value)

        if datatype == 'date-time':
            to_return[key] = {
                'type': ['null', 'string'],
                'format': 'date-time',
            }
        else:
            to_return[key] = {
                'type': ['null', datatype],
            }

    return to_return
