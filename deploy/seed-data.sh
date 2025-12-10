#!/bin/bash
# seed default people and tricks into the database

cd /opt/trickyclip/deploy

echo "seeding people and tricks..."

# add people
docker compose exec -T backend python << 'EOF'
from app.core.db import engine
from sqlmodel import Session
from app.models import Person, Trick
from uuid import uuid4

with Session(engine) as session:
    # add default people (customize these!)
    people_data = [
        {"display_name": "Miller-Downey", "slug": "miller-downey"},
        {"display_name": "BROLL", "slug": "BROLL"},
    ]
    
    for p in people_data:
        existing = session.query(Person).filter(Person.slug == p["slug"]).first()
        if not existing:
            person = Person(**p)
            session.add(person)
            print(f"Added person: {p['display_name']}")
    
    # add common rail tricks
    tricks_data = [
        # rail tricks
        {"name": "50-50", "category": "rail"},
        {"name": "5-0", "category": "rail"},
        {"name": "noseslide", "category": "rail"},
        {"name": "tailslide", "category": "rail"},
        {"name": "boardslide", "category": "rail"},
        {"name": "lipslide", "category": "rail"},
        {"name": "k-fed", "category": "rail"},
        {"name": "front-board", "category": "rail"},
        {"name": "back-board", "category": "rail"},
        {"name": "nosepress", "category": "rail"},
        {"name": "tailpress", "category": "rail"},
        {"name": "swap-50-50", "category": "rail"},
        
        # jump/spin tricks
        {"name": "180", "category": "jump"},
        {"name": "360", "category": "jump"},
        {"name": "540", "category": "jump"},
        {"name": "720", "category": "jump"},
        {"name": "backflip", "category": "jump"},
        {"name": "frontflip", "category": "jump"},
        {"name": "rodeo", "category": "jump"},
        {"name": "cork", "category": "jump"},
        {"name": "misty", "category": "jump"},
        
        # pretzel spins
        {"name": "pretzel-270-out", "category": "rail"},
        {"name": "pretzel-450-out", "category": "rail"},
        {"name": "pretzel-630-out", "category": "rail"},
        {"name": "front-270-out", "category": "rail"},
        {"name": "back-270-out", "category": "rail"},
        {"name": "front-450-out", "category": "rail"},
        {"name": "back-450-out", "category": "rail"},
        
        # b-roll
        {"name": "BROLL", "category": "other"},
    ]
    
    for t in tricks_data:
        existing = session.query(Trick).filter(Trick.name == t["name"]).first()
        if not existing:
            trick = Trick(**t)
            session.add(trick)
            print(f"Added trick: {t['name']}")
    
    session.commit()
    print("seeding complete!")
EOF

echo "✅ database seeded with people and tricks"


