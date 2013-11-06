"""
Restore Hazard Calculations dump produced with the
--dump-hazard-calculation option.

The general workflow to restore a calculation is the following:

1) Create a "staging" table for each target table (e.g. restore_gmf,
restore_oq_job, etc.)

2) Use "COPY FROM" statements to populate such table from the content
of the dump

3) INSERT the data SELECTed from the temporary tables INTO the
effective tables in the proper order RETURNING the id of the newly
created rows.

4) If the table is referenced in other tables, we create a temporary
table which maps the old id to the new one. Such table is used in the
SELECT at step 3 to insert the proper foreign key values
"""

import logging
import os

from openquake.engine.db import models
from django.db.models import fields

log = logging.getLogger()


def quote_unwrap(name):
    if name.startswith("\""):
        return name[1:-1]
    else:
        return name


def restore_tablename(original_tablename):
    _schema, tname = map(quote_unwrap, original_tablename.split('.'))
    return "htemp.restore_%s" % tname


def transfer_data(curs, model, **foreign_keys):
    def model_table(model, restore=False):
        original_tablename = "\"%s\"" % model._meta.db_table
        if restore:
            return restore_tablename(original_tablename)
        else:
            return "{}.{}".format(
                *map(quote_unwrap, original_tablename.split('.')))

    def model_fields(model):
        fs = ", ".join([f.column for f in model._meta.fields
                        if f.column != "id"
                        if not isinstance(f, fields.related.ForeignKey)])
        if fs:
            fs = ", " + fs
        return fs

    conn = curs.connection

    curs.execute(
        "ALTER TABLE %s ADD restore_id INT" % model_table(model))
    args = dict(
        table=model_table(model),
        fields=model_fields(model),
        restore_table=model_table(model, restore=True),
        fk_fields="", fk_joins="", new_fk_ids="")

    if foreign_keys:
        for fk, id_mapping in foreign_keys.iteritems():
            if fk is not None:
                curs.execute(
                    "CREATE TABLE temp_%s_translation("
                    "%s INT NOT NULL, new_id INT NOT NULL)" % (fk, fk))
                ids = ", ".join(["(%d, %d)" % (old_id, new_id)
                                 for old_id, new_id in id_mapping])
                curs.execute(
                    "INSERT INTO temp_%s_translation VALUES %s" % (fk, ids))

                args['fk_fields'] += ", %s" % fk
                args['fk_joins'] += (
                    "JOIN temp_%s_translation USING(%s) " % (fk, fk))
                args['new_fk_ids'] += ", temp_%s_translation.new_id" % fk

    query = """
INSERT INTO %(table)s (restore_id %(fields)s %(fk_fields)s)
SELECT id %(fields)s %(new_fk_ids)s
FROM %(restore_table)s AS restore
%(fk_joins)s
RETURNING  restore_id, %(table)s.id
""" % args

    curs.execute(query)
    old_new_ids = curs.fetchall()
    curs.execute(
        "ALTER TABLE %s DROP restore_id" % model_table(model))

    for fk in foreign_keys:
        curs.execute("DROP TABLE temp_%s_translation" % fk)

    conn.commit()

    return old_new_ids


def safe_restore(curs, filename, original_tablename):
    """
    Restore a postgres table into the database, by skipping the ids
    which are already taken. Assume that the first field of the table
    is an integer id and that gzfile.name has the form
    '/some/path/tablename.csv.gz' The file is restored in blocks to
    avoid memory issues.

    :param curs: a psycopg2 cursor
    :param filename: the path to the csv dump
    :param str tablename: full table name
    """
    # keep in memory the already taken ids
    conn = curs.connection
    tablename = restore_tablename(original_tablename)
    try:
        curs.execute("DROP TABLE IF EXISTS %s" % tablename)
        curs.execute(
            "CREATE TABLE %s AS SELECT * FROM %s WHERE 0 = 1" % (
                tablename, original_tablename))
        curs.copy_expert(
            """COPY %s FROM stdin
               WITH (FORMAT 'csv', HEADER true, ENCODING 'utf8')""" % (
                       tablename), file(os.path.abspath(filename)))
    except Exception as e:
        conn.rollback()
        log.error(str(e))
        raise
    else:
        conn.commit()


def hazard_restore(conn, directory):
    """
    Import a tar file generated by the HazardDumper.

    :param conn: the psycopg2 connection to the db
    :param directory: the pathname to the directory with the .gz files
    """
    filenames = os.path.join(directory, 'FILENAMES.txt')
    curs = conn.cursor()

    created = []
    for line in open(filenames):
        fname = line.rstrip()
        tname = fname[:-4]  # strip .csv

        fullname = os.path.join(directory, fname)
        log.info('Importing %s...', fname)
        created.append(tname)
        safe_restore(curs, fullname, tname)
    hc_ids = transfer_data(curs, models.HazardCalculation)
    lt_ids = transfer_data(
        curs, models.LtRealization, hazard_calculation_id=hc_ids)
    transfer_data(
        curs, models.HazardSite, hazard_calculation_id=hc_ids)
    job_ids = transfer_data(
        curs, models.OqJob, hazard_calculation_id=hc_ids)
    out_ids = transfer_data(
        curs, models.Output, oq_job_id=job_ids)
    ses_collection_ids = transfer_data(
        curs, models.SESCollection,
        output_id=out_ids, lt_realization_id=lt_ids)
    ses_ids = transfer_data(
        curs, models.SES, ses_collection_id=ses_collection_ids)
    transfer_data(curs, models.SESRupture, ses_id=ses_ids)

    curs = conn.cursor()
    try:
        for tname in reversed(created):
            query = "DROP TABLE %s" % restore_tablename(tname)
            curs.execute(query)
            log.info("Dropped %s" % restore_tablename(tname))
    except:
        conn.rollback()
    else:
        conn.commit()
    log.info('Restored %s', directory)
    return [new_id for _, new_id in hc_ids]
