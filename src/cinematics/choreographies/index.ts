import type { Role } from '../../contracts';
import { bishop } from './bishop';
import { king } from './king';
import { knight } from './knight';
import { pawn } from './pawn';
import { queen } from './queen';
import { rook } from './rook';
import type { Choreography } from './types';

export const CHOREOGRAPHIES: Record<Role, Choreography> = { pawn, rook, knight, bishop, queen, king };
export { bishop, king, knight, pawn, queen, rook };
