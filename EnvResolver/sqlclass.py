from peewee import *
from playhouse.pool import PooledPostgresqlExtDatabase, PostgresqlDatabase, PooledPostgresqlDatabase
database = PooledPostgresqlDatabase('PyDepResolver', max_connections=16, stale_timeout=300, **{
                                    'host': '127.0.0.1', 'port': 5432, 'user': 'xxx', 'password': 'xxx'})


def init_database():
    db = PooledPostgresqlDatabase('PyDepResolver', max_connections=16, stale_timeout=300, **{
                                  'host': '127.0.0.1', 'port': 5432, 'user': 'xxx', 'password': 'xxx'})
    return db


def init_models(db):
    class BaseModel(Model):
        class Meta:
            database = database

    class BenchmarkForDependency(BaseModel):
        dependency_graph = TextField(null=True)
        edge_level_correct = BooleanField(null=True)
        id = IntegerField(constraints=[SQL("DEFAULT nextval('benchmark_for_dependency_id_seq'::regclass)")])
        name = TextField(null=True)
        node_level_correct = BooleanField(null=True)
        own_dependency_graph = TextField(null=True)
        own_pinned_dependency = TextField(null=True)
        pinned_dependency = TextField(null=True)
        version = TextField(null=True)

        class Meta:
            table_name = 'benchmark_for_dependency'
            indexes = (
                (('name', 'version'), True),
            )
            primary_key = False
    
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
    if db.is_closed():
        db.connect()
    return (ProjectsMetadata, BenchmarkForDependency)
