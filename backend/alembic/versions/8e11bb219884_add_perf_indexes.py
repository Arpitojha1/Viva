"""add perf indexes

Revision ID: 8e11bb219884
Revises: 41229c186e65
Create Date: 2026-09-20 00:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.schema import Sequence, CreateIndex, DropIndex

# revision identifiers, used by Alembic.
revision: str = '8e11bb219884'
down_revision: Union[str, None] = '41229c186e65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add non-blocking vector HNSW index for cosine distance
    # Requires setting statement timeout or transactional=False if creating concurrently,
    # but for simple Alembic we can use standard CREATE INDEX if it's not a large table, 
    # but best practice for pgvector is CREATE INDEX.
    # Note: postgresql_ops={'embedding': 'vector_cosine_ops'} is needed for <=> queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chunks_embedding_cosine ON chunks USING hnsw (embedding vector_cosine_ops);"
    )

    # 2. Add foreign key indexes
    op.create_index('ix_questions_session_id', 'questions', ['session_id'])
    op.create_index('ix_answers_question_id', 'answers', ['question_id'])


def downgrade() -> None:
    op.drop_index('ix_answers_question_id', table_name='answers')
    op.drop_index('ix_questions_session_id', table_name='questions')
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_cosine;")
