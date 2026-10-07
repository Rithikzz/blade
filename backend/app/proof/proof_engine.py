import os
import json
from .schemas import ProofPackage, ProofRequest, IntegrityResponse
from .evidence_builder import build_proof_package
from .hashing import sha256_json

PROOFS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'proofs')
os.makedirs(PROOFS_DIR, exist_ok=True)

def generate_proof(request: ProofRequest) -> ProofPackage:
    proof = build_proof_package(request)
    _save_proof(proof)
    return proof

def _save_proof(proof: ProofPackage):
    path = os.path.join(PROOFS_DIR, f"{proof.proof_id}.json")
    with open(path, 'w') as f:
        json.dump(proof.model_dump(), f, indent=2)

def get_proof(proof_id: str) -> dict:
    path = os.path.join(PROOFS_DIR, f"{proof_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)

def check_integrity(proof_id: str) -> IntegrityResponse:
    proof_data = get_proof(proof_id)
    if not proof_data:
        return None
        
    stored_hash = proof_data.get('hashes', {}).get('proof_package_hash')
    
    # Recalculate hash by setting it to None first
    proof_data['hashes']['proof_package_hash'] = None
    calculated_hash = sha256_json(proof_data)
    
    return IntegrityResponse(
        proof_id=proof_id,
        integrity_valid=stored_hash == calculated_hash,
        stored_hash=stored_hash or "none",
        calculated_hash=calculated_hash
    )
