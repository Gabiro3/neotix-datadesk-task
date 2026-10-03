"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-30

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE user_role AS ENUM ('client', 'operator', 'admin');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE episode_quality AS ENUM ('good', 'usable', 'bad');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE request_status AS ENUM (
                'submitted', 'in_progress', 'delivered', 'accepted', 'rejected'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            role user_role NOT NULL,
            organisation VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS episodes (
            id SERIAL PRIMARY KEY,
            episode_id VARCHAR(64) NOT NULL,
            robot_id VARCHAR(64) NOT NULL,
            task_name VARCHAR(255) NOT NULL,
            recorded_at TIMESTAMPTZ NOT NULL,
            duration_seconds INTEGER NOT NULL,
            operator_name VARCHAR(255) NOT NULL,
            quality episode_quality NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_episodes_episode_id ON episodes (episode_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_episodes_robot_id ON episodes (robot_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_episodes_task_name ON episodes (task_name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_episodes_recorded_at ON episodes (recorded_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_episodes_quality ON episodes (quality);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_episodes_task_quality ON episodes (task_name, quality);")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL REFERENCES users(id),
            task_name VARCHAR(255) NOT NULL,
            episodes_requested INTEGER NOT NULL,
            deadline TIMESTAMPTZ NOT NULL,
            notes TEXT,
            status request_status NOT NULL DEFAULT 'submitted',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_requests_client_id ON requests (client_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_requests_task_name ON requests (task_name);")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id SERIAL PRIMARY KEY,
            request_id INTEGER NOT NULL REFERENCES requests(id),
            episode_id INTEGER NOT NULL REFERENCES episodes(id),
            assigned_by_id INTEGER NOT NULL REFERENCES users(id),
            assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_assignment_episode UNIQUE (episode_id),
            CONSTRAINT uq_assignment_request_episode UNIQUE (request_id, episode_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_assignments_request_id ON assignments (request_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_assignments_episode_id ON assignments (episode_id);")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS request_events (
            id SERIAL PRIMARY KEY,
            request_id INTEGER NOT NULL REFERENCES requests(id),
            actor_id INTEGER NOT NULL REFERENCES users(id),
            from_status request_status,
            to_status request_status NOT NULL,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_request_events_request_id ON request_events (request_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS request_events;")
    op.execute("DROP TABLE IF EXISTS assignments;")
    op.execute("DROP TABLE IF EXISTS requests;")
    op.execute("DROP TABLE IF EXISTS episodes;")
    op.execute("DROP TABLE IF EXISTS users;")
    op.execute("DROP TYPE IF EXISTS request_status;")
    op.execute("DROP TYPE IF EXISTS episode_quality;")
    op.execute("DROP TYPE IF EXISTS user_role;")
