# ADR-0012: Personal data on the change-capture path

Status: Proposed
Date: 2026-09-14
Supersedes: part of ADR-0006, for the raw zone on the CDC path

## What I'm deciding

What happens to names, emails, phone numbers, licence numbers and plates when
they leave Postgres and land in the lake. ADR-0006 decided the governance model
for the project as a whole. This one covers the part of it that phase 4 breaks.

## The gap in ADR-0006

ADR-0006 put direct identifiers in a restricted raw zone and said erasure is a
delete followed by a vacuum once retention passes. That works because Delta can
delete. The same ADR says so itself, that plain parquet on a lake can't.

Phase 4 lands raw as plain Parquet files written by DMS. So the raw zone is now
exactly the case ADR-0006 named as the one where deletion doesn't work. Every
update to a rider writes another file containing that rider, and none of those
files can have a row removed from them.

## The call

Personal data doesn't reach the raw zone in readable form at all.

Names come out entirely, using a rule that drops the column before it's written.
A ride-hailing analytics model has no use for them. Email, phone, licence number
and plate get replaced with a SHA-256 hash by DMS itself, using the masking rules
it has had since version 3.5.4. The value never lands in clear, but rows can
still be matched across tables. Surrogate keys like rider_id pass through
untouched, since a number that means nothing outside this database identifies
nobody on its own.

On top of that, the raw change prefixes get a short lifecycle rule and expire.
Raw is a landing area on the way to bronze, not an archive. Anything that needs
to last lives in Delta, where a delete is a delete.

That combination is what fixes the ADR-0006 gap. Raw can't be deleted from, so
raw holds nothing worth deleting and doesn't hold it for long.

## What hashing does and doesn't do

Hashing is pseudonymisation, not anonymisation. The data protection guidance is
clear that pseudonymised data is still personal data, because the person can
still be picked out indirectly. Only genuinely anonymous data falls outside
the rules. So a hashed email still carries obligations, including erasure. It
lowers the risk, it does not end the responsibility. Saying otherwise would be
the kind of claim that falls apart the moment someone who knows the area reads
it.

Two limits worth naming rather than hiding.

The masking happens on the replication instance. That means the real values are
read out of Postgres, cross the tunnel, and sit in memory in DMS before they're
transformed. They never reach S3, and that's the part that matters here. But the
boundary isn't at the source, and pretending it is would be wrong.

The built-in mask is a plain hash with no secret mixed in, so anyone holding the
output and a list of likely inputs can work backwards. Email addresses and plates
are guessable enough for that to be real. A keyed hash would fix it, and the
obvious place to put the key is a secret rather than the task definition sitting
in git. I'm not solving that inside DMS. Where a keyed value is genuinely needed,
it gets derived in the transform into bronze. That's where there's somewhere
safe to keep the key.

I am not a lawyer and this is a portfolio project with invented people in it. If
these were real subjects, this ADR would need actual legal review rather than my
reading of the guidance.

## Alternatives I turned down

**Keep the identifiers in raw and control access with bucket policy and IAM.**
This is what ADR-0006 originally described and it's what a lot of real platforms
do, because raw fidelity is worth something and the restrictions are enforceable.
It fails here for one specific reason. Erasure on plain Parquet means rewriting
files, and there is no machinery in this project to do that. Access control keeps
people out of the data. It doesn't get a person out of the data.

**Hash everything including the surrogate keys.** Pointless, since rider_id
identifies nobody outside this database and hashing it would break every join
for no gain.

**Encrypt the columns instead of hashing them.** Reversible, so the data stays
fully personal. I've added key management for nothing too, since nothing in
this project needs the original values back.

**A token vault, where real values live in one guarded table and everything else
holds tokens.** ADR-0006 already turned this down and the reasoning still holds.
It's for data you can't reach to delete, like backups or copies someone else
holds. This project owns every copy.

**Deal with it later in Unity Catalog.** Column masks in Unity Catalog are the
right tool for the tables it governs, and it governs nothing in the raw zone.
Waiting means the identifiers are already in S3 in files I can't edit, and the
control arrives after the problem.

## What I'm giving up

The real email and phone are gone from the lake permanently. If a genuine need
turned up later, a support lookup or a regulator asking about one person, the
answer would have to come from the source database. For this project that's
correct. In a company it would be a decision to make with people outside the
data team.

Reprocessing loses fidelity too. Rebuilding bronze from raw can never recover
what was never written.

Short retention on raw means no long raw history to replay, which is the same
cost ADR-0006 already accepted.

## What would flip this

- A real use case needing the original values in the platform, which would push
  this back toward restricted raw with proper access control and a way to rewrite
  files.
- Raw becoming Delta rather than plain Parquet, which would make deletion
  possible and make this whole decision unnecessary.
- Real subjects and a real regulator, where unsalted hashing wouldn't be good
  enough and a keyed scheme would stop being optional.
