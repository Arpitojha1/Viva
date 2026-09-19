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
    op.get_bind().execution_options(isolation_level="AUTOCOMMIT")
    op.execute(
        "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_chunks_embedding_cosine ON chunks USING hnsw (embedding vector_cosine_ops);"
    )

    # 2. Add foreign key indexes
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_questions_session_id ON questions (session_id);")
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_answers_question_id ON answers (question_id);")


def downgrade() -> None:
    op.get_bind().execution_options(isolation_level="AUTOCOMMIT")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_answers_question_id;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_questions_session_id;")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_chunks_embedding_cosine;")
