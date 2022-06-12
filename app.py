import strawberry

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter
from sqlalchemy import select

from strawberry.dataloader import DataLoader

from typing import Optional

import models


"""
Each class has a marshal method.
This method is what allows taking in an SQLAlchemy model and create a Strawberry type class instance from it.
Strawberry uses strawberry.ID to represent a unique identifier to an object.
Strawberry provides a few scalar types by default that work just like strawberry.ID.
It is up to the developer on how to use those to map the SQLAlchemy data to this custom type class attribute.
Generally, finding the best and closely resembling alternative to the SQLAlchemy column type and using it is for the best.
"""


@strawberry.type
class Author:
    id: strawberry.ID
    name: str

    @classmethod
    def marshal(cls, model: models.Author) -> "Author":
        return cls(id=strawberry.ID(str(model.id)), name=model.name)


@strawberry.type
class Book:
    id: strawberry.ID
    name: str
    author: Optional[Author] = None

    @classmethod
    def marshal(cls, model: models.Book) -> "Book":
        return cls(
            id=strawberry.ID(str(model.id)),
            name=model.name,
            author=Author.marshal(model.author) if model.author else None,
        )


@strawberry.type
class AuthorExists:
    message: str = "Author with this name already exists"


@strawberry.type
class AuthorNotFound:
    message: str = "Couldn't find an author with the supplied name"


@strawberry.type
class AuthorNameMissing:
    message: str = "Please supply an author name"


# The AddBookResponse and AddAuthorResponse types are union types and
# can be either of the three (or two) types listed in the tuple.
AddBookResponse = strawberry.union(
    "AddBookResponse", (Book, AuthorNotFound, AuthorNameMissing))
AddAuthorResponse = strawberry.union(
    "AddAuthorResponse", (Author, AuthorExists))


@strawberry.type
class Query:
    @strawberry.field
    async def books(self) -> list[Book]:
        async with models.get_session() as s:
            sql = select(models).order_by(models.Book.name)
            db_books = (await s.execute(sql)).scalars().unique().all()
            return [Book.marshal(book) for book in db_books]

    @strawberry.field
    async def authors(self) -> list[Author]:
        async with models.get_session() as s:
            sql = select(models.Author).order_by(models.Author.name)
            db_authors = (await s.execute(sql)).scalars().unique().all()
            return [Author.marshal(author) for author in db_authors]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def add_book(self, name: str, author_name: Optional[str]) -> AddBookResponse:
        with models.get_session() as s:
            db_author = None
            if not author_name:
                return AuthorNameMissing()
            sql = select(models.Author).where(
                models.Author.name == author_name)
            db_author = (await s.execute(sql)).scalars().first()
            if not db_author:
                return AuthorNotFound()
            db_book = models.Book(name=name, author_id=db_author)
            s.add(db_book)
            await s.commit()
        return Book.marshal(db_book)

    @strawberry.mutation
    async def add_author(self, name: str) -> AddAuthorResponse:
        async with models.get_session() as s:
            sql = select(models.Author).where(models.Author.name == name)
            existing_db_author = (await s.execute(sql)).first()
            if existing_db_author:
                return AuthorExists()
            db_author = models.Author(name=name)
            s.add(db_author)
            await s.commit()
        return Author.marshal(db_author)


async def load_books_by_author(keys: list) -> list[Book]:
    async with models.get_session() as s:
        all_queries = [select(models.Book).where(
            models.Book.author_id == key) for key in keys]
        data = [(await s.execute(sql)).scalars().unique().all() for sql in all_queries]
        print(keys, data)
    return data


async def load_author_by_book(keys: list) -> list[Book]:
    async with models.get_session() as s:
        sql = select(models.Author).where(models.Author.id in keys)
        data = (await s.execute(sql)).scalars().unique().all()
    if not data:
        data.append([])
    return data


async def get_context() -> dict:
    return {
        "author_by_book": DataLoader(load_fn=load_author_by_book),
        "books_by_author": DataLoader(load_fn=load_books_by_author),
    }

schema = strawberry.Schema(query=Query, mutation=Mutation)

graphql_app = GraphQLRouter(schema)

app = FastAPI()
app.include_router(graphql_app, prefix="/graphql")
