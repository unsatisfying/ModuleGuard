from peewee import *

database = PostgresqlDatabase('MCDownload', **{'host': 'localhost', 'user': 'zrf', 'password': '123456'})

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class ProjectsMetadata(BaseModel):
    dependency = TextField(null=True)
    dependency_graph = TextField(null=True)
    id = IntegerField(constraints=[SQL("DEFAULT nextval('projects_metadata_id_seq'::regclass)")])
    metadata = TextField(null=True)
    module_path = TextField(null=True)
    name = TextField(index=True, null=True)
    pinned_dependency = TextField(null=True)
    parsed_type_for_dep = TextField(null=True)
    version = TextField(null=True)
    version_struct = TextField(null=True)
    yanked = BooleanField(null=True)

    class Meta:
        table_name = 'projects_metadata'
        indexes = (
            (('name', 'version'), False),
            (('name', 'version_struct'), False),
        )
        primary_key = False
