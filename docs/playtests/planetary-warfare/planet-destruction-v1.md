# Planet destruction

The first destroy on a hostile planet with no fighters and no shields sets every colonist pool to 0. The planet stays, and so do its treasury, stockpile, and fighters. The second destroy removes the planet. Those goods are not refunded. A defended planet and a corp planet stay put, and alignment does not change.

The siege grid does not call this action, so those cells did not change.

| Step | Ok | Planet before | Planet after | Colonists | Alignment | Sector |
|---|---|---|---|---:|---:|---:|
| kill | yes | yes | yes | 0 | -50 | 40 |
| remove 1 | yes | yes | yes | 0 | -50 | 40 |
| remove 2 | yes | yes | no | 0 | -100 | 40 |
| defended | no | yes | yes | 12 | 0 | 40 |
| corp | no | yes | yes | 12 | 0 | 40 |
