
"""
type decorator converts the class into a GraphQL type.
Strawberry automatically converts underscore into camelCase.
"""


import strawberry

from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI


authors: list[str] = []


@strawberry.type
class Query:

    @strawberry.field
    def all_authors(self) -> list[str]:
        return authors


"""
Queries — A type of request sent to the server to retrieve data/records
Mutations — A type of request sent to the server to create/update/delete data/record
Types — The objects that one uses to interact with in GraphQL. These represent the data/records/errors and everything in between.
Resolver — A function that populates the data for a single field in the schema.
"""


@strawberry.type
class Mutation:
    @strawberry.field
    def add_author(self, name: str) -> str:
        authors.append(name)
        return name


schema = strawberry.Schema(query=Query, mutation=Mutation)


graphql_app = GraphQLRouter(schema)
app = FastAPI()

app.include_router(graphql_app, prefix="/graphql")
