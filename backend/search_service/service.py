from typing import List, Literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, literal, case
from backend.commons.models import Paragraph
from backend.commons.elasticsearch_client import ElasticsearchClient


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.es = ElasticsearchClient.get_client()

    async def search_paragraphs(
        self, words: List[str], operator: Literal["and", "or"]
    ) -> List[Paragraph]:
        # Build ES boolean query
        clauses = [
            {
                "match": {
                    "content": {
                        "query": w,
                        "fuzziness": 2
                    }
                }
            }
            for w in words
        ]

        bool_clause = {}
        if operator == "or":
            bool_clause["should"] = clauses
            bool_clause["minimum_should_match"] = 1
        else:
            bool_clause["must"] = clauses

        query_body = {"bool": bool_clause}

        print("query_body: ", query_body)

        resp = await ElasticsearchClient.search(
            index="paragraphs",
            query=query_body,
            size=10 # We can put this in Constants
        )

        hits = resp["hits"]["hits"]
        paragraph_ids = [int(hit["_id"]) for hit in hits]
        if not paragraph_ids:
            return []  # no matches

        # Fetch from DB in same order as ES ranking
        # Build a CASE statement for ordering based on ES rank
        whens = {pid: len(paragraph_ids) - idx for idx, pid in enumerate(paragraph_ids)}
        ordering = case(whens, value=Paragraph.id, else_=0).desc()

        stmt = select(Paragraph).where(Paragraph.id.in_(paragraph_ids)).order_by(ordering)
        result = await self.db.execute(stmt)
        paragraphs = result.scalars().all()

        return paragraphs
