"""Local administrator bootstrap, never exposed as a public HTTP endpoint."""
import argparse, getpass, secrets
from sqlalchemy import select
from .database import database, User
from .security import password_hash

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('role',choices=['admin','coordinator'])
    parser.add_argument('--email',required=True)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    password=getpass.getpass('New password (10+ characters): ')
    if len(password)<10: raise SystemExit('Password must have at least 10 characters')
    if getpass.getpass('Repeat password: ')!=password: raise SystemExit('Passwords do not match')
    with database()() as s:
        email=args.email.strip().lower()
        if s.scalar(select(User).where(User.email==email)): raise SystemExit('Email already exists; no account changed')
        s.add(User(id='CL-'+secrets.token_hex(8).upper(),name=args.name.strip(),email=email,password=password_hash(password),role=args.role))
        s.commit()
    print('Account created. Sign in through the portal.')

if __name__=='__main__': main()
