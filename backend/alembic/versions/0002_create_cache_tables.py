"""Create cache tables for satellite positions and passes

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create satellite_positions_cache table
    op.create_table('satellite_positions_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('norad_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.DECIMAL(precision=10, scale=8), nullable=False),
        sa.Column('longitude', sa.DECIMAL(precision=11, scale=8), nullable=False),
        sa.Column('altitude', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('velocity', sa.DECIMAL(precision=10, scale=2), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['norad_id'], ['satellites.norad_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_positions_cache_norad_timestamp', 'satellite_positions_cache', ['norad_id', 'timestamp'], unique=False)
    op.create_index('idx_positions_cache_timestamp', 'satellite_positions_cache', ['timestamp'], unique=False)
    op.create_index('idx_positions_cache_created_at', 'satellite_positions_cache', ['created_at'], unique=False)
    op.create_index(op.f('ix_satellite_positions_cache_id'), 'satellite_positions_cache', ['id'], unique=False)
    op.create_index(op.f('ix_satellite_positions_cache_norad_id'), 'satellite_positions_cache', ['norad_id'], unique=False)

    # Create satellite_passes_cache table
    op.create_table('satellite_passes_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('norad_id', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.DECIMAL(precision=10, scale=8), nullable=False),
        sa.Column('longitude', sa.DECIMAL(precision=11, scale=8), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('max_elevation', sa.DECIMAL(precision=5, scale=2), nullable=False),
        sa.Column('start_azimuth', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('end_azimuth', sa.DECIMAL(precision=5, scale=2), nullable=True),
        sa.Column('magnitude', sa.DECIMAL(precision=4, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['norad_id'], ['satellites.norad_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_passes_cache_location_time', 'satellite_passes_cache', ['latitude', 'longitude', 'start_time'], unique=False)
    op.create_index('idx_passes_cache_norad_time', 'satellite_passes_cache', ['norad_id', 'start_time'], unique=False)
    op.create_index('idx_passes_cache_expires', 'satellite_passes_cache', ['expires_at'], unique=False)
    op.create_index('idx_passes_cache_created_at', 'satellite_passes_cache', ['created_at'], unique=False)
    op.create_index(op.f('ix_satellite_passes_cache_id'), 'satellite_passes_cache', ['id'], unique=False)
    op.create_index(op.f('ix_satellite_passes_cache_norad_id'), 'satellite_passes_cache', ['norad_id'], unique=False)


def downgrade() -> None:
    # Drop cache tables
    op.drop_table('satellite_passes_cache')
    op.drop_table('satellite_positions_cache')