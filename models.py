import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker


Base = declarative_base()


class Author(Base):
    __tablename__ = 'authors'

    id: str = Column(Integer, primary_key=True)
    name: str = Column(String(50), nullable=False)

    # relationship attribute that helps navigate the relationships between models.
    # not stored in the authors table as a separate column.
    # Used to back populate the books attribute as author.
    # Used to employ book.author to access the linked author for a book.
    books: list["Book"] = relationship(
        "Book", lazy="joined", back_populates="author")


class Book(Base):
    __tablename__ = 'books'
    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String(50), nullable=False)
    author_id: Optional[int] = Column(
        Integer, ForeignKey(Author.id), nullable=True)

    author: Optional["Author"] = relationship(
        Author, lazy="joined", back_populates="books")


engine = create_async_engine(
    "sqlite+aiosqlite:///./database.db", connect_args={"check_same_thread": False}
)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        async with session.begin():
            try:
                yield session
            finally:
                await session.close()


async def _async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()


if __name__ == "__main__":
    print("Dropping and re/creating tables")
    asyncio.run(_async_main())
    print("Done.")
