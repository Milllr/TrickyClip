#!/usr/bin/env python3
"""
drive organizer CLI - audit and reorganize google drive clips

usage:
    python -m cli.drive_organizer audit
    python -m cli.drive_organizer reorganize --dry-run
    python -m cli.drive_organizer reorganize --execute
    python -m cli.drive_organizer set-locations
    python -m cli.drive_organizer missing-locations
"""
import argparse
import sys
import os

# add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.core.db import engine
from app.core.config import settings
from app.models import FinalClip, Person, Trick, Location, ClipPerson, CandidateSegment
from app.services.drive import drive_service
from app.services.filenames import slugify
from typing import Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class DriveFile:
    """represents a file found on google drive"""
    id: str
    name: str
    path: str  # full path from root
    parent_id: str
    mime_type: str
    size: int = 0


@dataclass
class AuditIssue:
    """represents an issue found during audit"""
    issue_type: str  # orphaned_db, orphaned_drive, wrong_path, old_naming, missing_location
    clip_id: Optional[str]
    drive_file_id: Optional[str]
    current_path: Optional[str]
    expected_path: Optional[str]
    details: str


class DriveOrganizer:
    """main class for drive organization operations"""
    
    def __init__(self):
        self.drive = drive_service
        self.root_folder_id = settings.GOOGLE_DRIVE_ROOT_FOLDER_ID
        self.issues: list[AuditIssue] = []
        self.drive_files: dict[str, DriveFile] = {}  # keyed by drive_file_id
        self.folder_tree: dict[str, str] = {}  # folder_id -> folder_path
        
    def scan_drive_recursive(self, folder_id: str, path: str = "") -> None:
        """recursively scan drive folder and build file index"""
        if not self.drive.service:
            print("error: drive service not initialized")
            return
            
        print(f"  scanning: {path or '/'}")
        
        query = f"'{folder_id}' in parents and trashed=false"
        try:
            results = self.drive.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, mimeType, size, parents)',
                pageSize=1000
            ).execute()
            
            items = results.get('files', [])
            
            for item in items:
                item_path = f"{path}/{item['name']}" if path else item['name']
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    # it's a folder, store path and recurse
                    self.folder_tree[item['id']] = item_path
                    self.scan_drive_recursive(item['id'], item_path)
                else:
                    # it's a file
                    self.drive_files[item['id']] = DriveFile(
                        id=item['id'],
                        name=item['name'],
                        path=item_path,
                        parent_id=item.get('parents', [''])[0],
                        mime_type=item['mimeType'],
                        size=int(item.get('size', 0))
                    )
        except Exception as e:
            print(f"error scanning {path}: {e}")
    
    def get_expected_path(self, clip: FinalClip, session: Session) -> str:
        """compute the expected path for a clip based on new folder structure"""
        # YEAR / PLACE / DAY / CATEGORY
        year = clip.date.strftime("%Y")
        day = clip.date.strftime("%Y-%m-%d")
        
        # get location
        if clip.location_id:
            location = session.get(Location, clip.location_id)
            place = location.name if location else "Unknown_Location"
        else:
            place = "Unknown_Location"
        
        # get primary person and category folder
        if clip.person_id:
            person = session.get(Person, clip.person_id)
            person_name = person.display_name if person else "Unknown"
        else:
            person_name = None
        
        # determine category folder name
        category = clip.category.upper()
        if category == "TRICK" and person_name:
            category_folder = f"{person_name}_TRICKS"
        elif category == "CRASH" and person_name:
            category_folder = f"{person_name}_CRASH"
        elif category == "BROLL":
            category_folder = "BROLL"
        else:
            category_folder = "MISC"
        
        # build expected filename
        expected_filename = self.get_expected_filename(clip, session)
        
        return f"{year}/{place}/{day}/{category_folder}/{expected_filename}"
    
    def get_expected_filename(self, clip: FinalClip, session: Session) -> str:
        """generate expected filename in new format: DATE__TRICK__PEOPLE__VERSION.mp4"""
        date_str = clip.date.strftime("%Y-%m-%d")
        
        # get trick name
        if clip.trick_id:
            trick = session.get(Trick, clip.trick_id)
            trick_name = trick.name if trick else "Unknown"
        else:
            trick_name = clip.category.capitalize()
        
        # get all people for this clip (primary + secondary from clip_people)
        people_names = []
        
        # primary person
        if clip.person_id:
            primary = session.get(Person, clip.person_id)
            if primary:
                people_names.append(primary.display_name)
        
        # secondary people from clip_people table
        clip_people = session.exec(
            select(ClipPerson)
            .where(ClipPerson.clip_id == clip.id)
            .order_by(ClipPerson.priority)
        ).all()
        
        for cp in clip_people:
            if cp.person_id != clip.person_id:  # skip primary
                person = session.get(Person, cp.person_id)
                if person:
                    people_names.append(person.display_name)
        
        people_str = "_".join(people_names) if people_names else "Unknown"
        
        # extract version from existing filename or default to v001
        import re
        version_match = re.search(r'__v(\d+)\.mp4$', clip.filename)
        version = int(version_match.group(1)) if version_match else 1
        
        return f"{date_str}__{trick_name}__{people_str}__v{version:03d}.mp4"
    
    def audit(self) -> list[AuditIssue]:
        """perform full audit of drive vs database"""
        print("\n=== DRIVE AUDIT ===\n")
        
        # scan drive
        print("📂 scanning google drive...")
        self.scan_drive_recursive(self.root_folder_id)
        print(f"   found {len(self.drive_files)} files on drive\n")
        
        # load all clips from database
        print("📊 loading clips from database...")
        with Session(engine) as session:
            clips = session.exec(select(FinalClip)).all()
            print(f"   found {len(clips)} clips in database\n")
            
            # check for orphaned db records (in DB but not on drive)
            print("🔍 checking for orphaned database records...")
            for clip in clips:
                if clip.drive_file_id and clip.drive_file_id not in self.drive_files:
                    self.issues.append(AuditIssue(
                        issue_type="orphaned_db",
                        clip_id=str(clip.id),
                        drive_file_id=clip.drive_file_id,
                        current_path=None,
                        expected_path=None,
                        details=f"clip '{clip.filename}' not found on drive"
                    ))
            
            # check for orphaned drive files (on drive but not in DB)
            print("🔍 checking for orphaned drive files...")
            db_drive_ids = {c.drive_file_id for c in clips if c.drive_file_id}
            
            # only check video files in year folders (skip processed, dump, sorted archive)
            for drive_id, drive_file in self.drive_files.items():
                if not drive_file.mime_type.startswith('video/'):
                    continue
                # skip system folders
                if any(drive_file.path.startswith(f) for f in ['processed/', 'sorted archive/', 'dump/']):
                    continue
                    
                if drive_id not in db_drive_ids:
                    self.issues.append(AuditIssue(
                        issue_type="orphaned_drive",
                        clip_id=None,
                        drive_file_id=drive_id,
                        current_path=drive_file.path,
                        expected_path=None,
                        details=f"file '{drive_file.name}' not in database"
                    ))
            
            # check for wrong paths and old naming
            print("🔍 checking folder structure and naming...")
            for clip in clips:
                if not clip.drive_file_id or clip.drive_file_id not in self.drive_files:
                    continue
                    
                drive_file = self.drive_files[clip.drive_file_id]
                expected_path = self.get_expected_path(clip, session)
                
                # check path
                if drive_file.path != expected_path:
                    self.issues.append(AuditIssue(
                        issue_type="wrong_path",
                        clip_id=str(clip.id),
                        drive_file_id=clip.drive_file_id,
                        current_path=drive_file.path,
                        expected_path=expected_path,
                        details="file in wrong folder structure"
                    ))
                
                # check for missing location
                if not clip.location_id:
                    self.issues.append(AuditIssue(
                        issue_type="missing_location",
                        clip_id=str(clip.id),
                        drive_file_id=clip.drive_file_id,
                        current_path=drive_file.path,
                        expected_path=None,
                        details=f"clip '{clip.filename}' has no location set"
                    ))
        
        return self.issues
    
    def print_audit_report(self) -> None:
        """print formatted audit report"""
        print("\n" + "=" * 60)
        print("=== DRIVE AUDIT REPORT ===")
        print("=" * 60 + "\n")
        
        print(f"files on drive: {len(self.drive_files)}")
        
        with Session(engine) as session:
            clips = session.exec(select(FinalClip)).all()
            print(f"clips in database: {len(clips)}")
        
        # group issues by type
        orphaned_db = [i for i in self.issues if i.issue_type == "orphaned_db"]
        orphaned_drive = [i for i in self.issues if i.issue_type == "orphaned_drive"]
        wrong_path = [i for i in self.issues if i.issue_type == "wrong_path"]
        missing_location = [i for i in self.issues if i.issue_type == "missing_location"]
        
        print(f"\n📋 ISSUES FOUND: {len(self.issues)}")
        print(f"  - {len(orphaned_db)} files in DB but not on drive (orphaned records)")
        print(f"  - {len(orphaned_drive)} files on drive but not in DB")
        print(f"  - {len(wrong_path)} files in wrong folder structure")
        print(f"  - {len(missing_location)} clips missing location metadata")
        
        if wrong_path:
            print("\n📁 FOLDER STRUCTURE ISSUES:")
            for issue in wrong_path[:10]:  # show first 10
                print(f"  [CURRENT]  {issue.current_path}")
                print(f"  [EXPECTED] {issue.expected_path}")
                print()
            if len(wrong_path) > 10:
                print(f"  ... and {len(wrong_path) - 10} more")
        
        if orphaned_db:
            print("\n⚠️  ORPHANED DB RECORDS:")
            for issue in orphaned_db[:5]:
                print(f"  - {issue.details}")
            if len(orphaned_db) > 5:
                print(f"  ... and {len(orphaned_db) - 5} more")
        
        if orphaned_drive:
            print("\n⚠️  ORPHANED DRIVE FILES:")
            for issue in orphaned_drive[:5]:
                print(f"  - {issue.current_path}")
            if len(orphaned_drive) > 5:
                print(f"  ... and {len(orphaned_drive) - 5} more")
        
        print("\n" + "=" * 60)
    
    def reorganize(self, dry_run: bool = True) -> None:
        """reorganize files to match expected structure and update database"""
        if dry_run:
            print("\n=== DRY RUN - NO CHANGES WILL BE MADE ===\n")
        else:
            print("\n=== EXECUTING REORGANIZATION ===\n")
        
        # first run audit if not already done
        if not self.issues:
            self.audit()
        
        wrong_path_issues = [i for i in self.issues if i.issue_type == "wrong_path"]
        
        if not wrong_path_issues:
            print("✅ no files need reorganization")
            return
        
        print(f"📁 {len(wrong_path_issues)} files to reorganize\n")
        
        success_count = 0
        error_count = 0
        
        with Session(engine) as session:
            for issue in wrong_path_issues:
                print(f"moving: {issue.current_path}")
                print(f"    to: {issue.expected_path}")
                
                if not dry_run:
                    try:
                        # parse expected path to get folder structure
                        path_parts = issue.expected_path.split('/')
                        filename = path_parts[-1]
                        folder_path = '/'.join(path_parts[:-1])
                        
                        # ensure folder structure exists
                        target_folder_id = self._ensure_folder_path(folder_path)
                        
                        if target_folder_id:
                            # move file to new folder
                            self.drive.move_file(issue.drive_file_id, target_folder_id)
                            
                            # rename file if needed
                            current_name = self.drive_files[issue.drive_file_id].name
                            if current_name != filename:
                                self.drive.service.files().update(
                                    fileId=issue.drive_file_id,
                                    body={'name': filename}
                                ).execute()
                                print(f"    renamed: {current_name} -> {filename}")
                            
                            # update database with new filename
                            if issue.clip_id:
                                clip = session.get(FinalClip, UUID(issue.clip_id))
                                if clip and clip.filename != filename:
                                    clip.filename = filename
                                    clip.updated_at = datetime.utcnow()
                                    session.add(clip)
                                    print(f"    📝 updated database filename")
                            
                            print("    ✅ moved successfully")
                            success_count += 1
                        else:
                            print("    ❌ failed to create target folder")
                            error_count += 1
                    except Exception as e:
                        print(f"    ❌ error: {e}")
                        error_count += 1
                
                print()
            
            # commit all database changes
            if not dry_run:
                session.commit()
        
        if dry_run:
            print("\n💡 run with --execute to apply these changes")
        else:
            print(f"\n✅ reorganization complete: {success_count} succeeded, {error_count} failed")
    
    def _ensure_folder_path(self, folder_path: str) -> Optional[str]:
        """ensure folder path exists on drive, returns folder id"""
        parts = folder_path.split('/')
        current_folder_id = self.root_folder_id
        
        for part in parts:
            if not part:
                continue
            try:
                current_folder_id = self.drive._ensure_folder(current_folder_id, part)
            except Exception as e:
                print(f"error creating folder {part}: {e}")
                return None
        
        return current_folder_id
    
    def set_locations_interactive(self) -> None:
        """interactively set locations for clips missing them"""
        print("\n=== SET LOCATIONS ===\n")
        
        with Session(engine) as session:
            # get clips missing location
            clips = session.exec(
                select(FinalClip)
                .where(FinalClip.location_id == None)
            ).all()
            
            if not clips:
                print("✅ all clips have locations set")
                return
            
            print(f"found {len(clips)} clips without locations\n")
            
            # get existing locations
            locations = session.exec(select(Location)).all()
            
            print("existing locations:")
            for i, loc in enumerate(locations, 1):
                print(f"  {i}. {loc.name}")
            print(f"  n. create new location")
            print()
            
            for clip in clips:
                print(f"\nclip: {clip.filename}")
                print(f"date: {clip.date}")
                print(f"session: {clip.session_name}")
                
                choice = input("\nselect location (number, 'n' for new, 's' to skip, 'q' to quit): ").strip().lower()
                
                if choice == 'q':
                    break
                elif choice == 's':
                    continue
                elif choice == 'n':
                    name = input("enter location name: ").strip()
                    if name:
                        new_loc = Location(
                            name=name,
                            slug=slugify(name)
                        )
                        session.add(new_loc)
                        session.flush()
                        clip.location_id = new_loc.id
                        session.add(clip)
                        locations.append(new_loc)
                        print(f"✅ created location '{name}' and assigned to clip")
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(locations):
                            clip.location_id = locations[idx].id
                            session.add(clip)
                            print(f"✅ assigned location '{locations[idx].name}'")
                        else:
                            print("invalid selection")
                    except ValueError:
                        print("invalid input")
            
            session.commit()
            print("\n✅ changes saved")
    
    def list_missing_locations(self) -> None:
        """list all clips missing location metadata"""
        print("\n=== CLIPS MISSING LOCATIONS ===\n")
        
        with Session(engine) as session:
            clips = session.exec(
                select(FinalClip)
                .where(FinalClip.location_id == None)
                .order_by(FinalClip.date)
            ).all()
            
            if not clips:
                print("✅ all clips have locations set")
                return
            
            print(f"found {len(clips)} clips without locations:\n")
            
            for clip in clips:
                print(f"  {clip.date} | {clip.session_name} | {clip.filename}")
            
            print(f"\n💡 run 'set-locations' to assign locations interactively")
    
    def queue_broken_clips_for_review(self, issue_types: list[str] = None) -> int:
        """
        reset broken clips to UNREVIEWED so they appear in sort queue.
        returns count of clips queued.
        """
        if issue_types is None:
            issue_types = ['missing_location', 'wrong_path', 'orphaned_db']
        
        queued = 0
        clip_ids_to_queue = set()
        
        for issue in self.issues:
            if issue.issue_type in issue_types and issue.clip_id:
                clip_ids_to_queue.add(UUID(issue.clip_id))
        
        if not clip_ids_to_queue:
            return 0
        
        with Session(engine) as session:
            for clip_id in clip_ids_to_queue:
                clip = session.get(FinalClip, clip_id)
                if not clip:
                    continue
                
                # find the segment and reset to UNREVIEWED
                segment = session.get(CandidateSegment, clip.candidate_segment_id)
                if segment and segment.status != "UNREVIEWED":
                    segment.status = "UNREVIEWED"
                    session.add(segment)
                    queued += 1
                    print(f"  ⏮️  queued: {clip.filename}")
            
            session.commit()
        
        return queued
    
    def auto_fix(self) -> None:
        """run audit and automatically queue broken clips for review"""
        print("\n=== AUTO-FIX MODE ===\n")
        
        # run audit first
        self.audit()
        self.print_audit_report()
        
        # filter issues that can be fixed by re-reviewing
        fixable_issues = [
            i for i in self.issues 
            if i.issue_type in ['missing_location', 'wrong_path']
        ]
        
        if not fixable_issues:
            print("\n✅ no issues require re-review")
            return
        
        print(f"\n🔧 queuing {len(fixable_issues)} clips for re-review...\n")
        
        queued = self.queue_broken_clips_for_review(['missing_location', 'wrong_path'])
        
        print(f"\n✅ queued {queued} clips for re-review")
        print("   they will appear in the sort queue when you reload the sort page")


def main():
    parser = argparse.ArgumentParser(
        description="drive organizer - audit and reorganize google drive clips"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="available commands")
    
    # audit command
    audit_parser = subparsers.add_parser("audit", help="scan drive and report issues")
    audit_parser.add_argument("--auto-fix", action="store_true", help="queue broken clips for re-review")
    
    # reorganize command
    reorg_parser = subparsers.add_parser("reorganize", help="reorganize files to correct structure")
    reorg_parser.add_argument("--dry-run", action="store_true", default=True, help="show what would change (default)")
    reorg_parser.add_argument("--execute", action="store_true", help="actually move files")
    
    # set-locations command
    subparsers.add_parser("set-locations", help="interactively set locations for clips")
    
    # missing-locations command
    subparsers.add_parser("missing-locations", help="list clips missing location metadata")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    organizer = DriveOrganizer()
    
    if args.command == "audit":
        if args.auto_fix:
            organizer.auto_fix()
        else:
            organizer.audit()
            organizer.print_audit_report()
    
    elif args.command == "reorganize":
        dry_run = not args.execute
        organizer.reorganize(dry_run=dry_run)
    
    elif args.command == "set-locations":
        organizer.set_locations_interactive()
    
    elif args.command == "missing-locations":
        organizer.list_missing_locations()


if __name__ == "__main__":
    main()

