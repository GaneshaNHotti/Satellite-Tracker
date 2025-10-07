"""Create initial tables for users, locations, satellites, and favorites

Revision ID: 0001
Revises: 
Create Date: 2024-01-15 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index('idx_users_active', 'users', ['is_active'], unique=False)
    op.create_index('idx_users_created_at', 'users', ['created_at'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_unique_constraint('uq_users_email', 'users', ['email'])

    # Create satellites table
    op.create_table('satellites',
        sa.Column('norad_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('launch_date', sa.Date(), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('norad_id')
    )
    op.create_index('idx_satellites_name', 'satellites', ['name'], unique=False)
    op.create_index('idx_satellites_category', 'satellites', ['category'], unique=False)
    op.create_index('idx_satellites_country', 'satellites', ['country'], unique=False)
    op.create_index('idx_satellites_created_at', 'satellites', ['created_at'], unique=False)
    op.create_index(op.f('ix_satellites_norad_id'), 'satellites', ['norad_id'], unique=False)

    # Create user_locations table
    op.create_table('user_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.DECIMAL(precision=10, scale=8), nullable=False),
        sa.Column('longitude', sa.DECIMAL(precision=11, scale=8), nullable=False),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('latitude >= -90 AND latitude <= 90', name='check_latitude_range'),
        sa.CheckConstraint('longitude >= -180 AND longitude <= 180', name='check_longitude_range'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_locations_user_id', 'user_locations', ['user_id'], unique=False)
    op.create_index('idx_user_locations_coords', 'user_locations', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_user_locations_created_at', 'user_locations', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_locations_id'), 'user_locations', ['id'], unique=False)

    # Create user_favorite_satellites table
    op.create_table('user_favorite_satellites',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('norad_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['norad_id'], ['satellites.norad_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'norad_id', name='uq_user_favorite_satellite')
    )
    op.create_index('idx_user_favorites_user_id', 'user_favorite_satellites', ['user_id'], unique=False)
    op.create_index('idx_user_favorites_norad_id', 'user_favorite_satellites', ['norad_id'], unique=False)
    op.create_index('idx_user_favorites_created_at', 'user_favorite_satellites', ['created_at'], unique=False)
    op.create_index(op.f('ix_user_favorite_satellites_id'), 'user_favorite_satellites', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('user_favorite_satellites')
    op.drop_table('user_locations')
    op.drop_table('satellites')
    op.drop_table('users')