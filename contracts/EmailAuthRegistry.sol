// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title  EmailAuthRegistry
 * @notice Stores SHA-256 message hashes on-chain to provide
 *         tamper-proof evidence of email authenticity.
 * @dev    Deployed on Ganache (local testnet, chainId 1337).
 *         Each hash is stored exactly once; duplicates are rejected.
 */
contract EmailAuthRegistry {

    // ── Events ────────────────────────────────────────────────────────────────
    /// @notice Emitted when a new message hash is registered
    event HashStored(
        bytes32 indexed msgHash,
        address indexed sender,
        uint256 timestamp
    );

    // ── Storage ───────────────────────────────────────────────────────────────
    address public owner;

    struct HashRecord {
        address sender;     // Ethereum address that stored the hash
        uint256 timestamp;  // Block timestamp of storage
        bool    exists;     // Existence flag
    }

    mapping(bytes32 => HashRecord) private hashRegistry;
    bytes32[]                      private allHashes;   // ordered list

    // ── Modifiers ─────────────────────────────────────────────────────────────
    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorised");
        _;
    }

    // ── Constructor ───────────────────────────────────────────────────────────
    constructor() {
        owner = msg.sender;
    }

    // ── Core Functions ────────────────────────────────────────────────────────

    /**
     * @notice Store a SHA-256 message hash.
     * @param  msgHash  32-byte hash (bytes32 representation of hex string)
     */
    function storeHash(bytes32 msgHash) external {
        require(msgHash != bytes32(0),          "Hash cannot be zero");
        require(!hashRegistry[msgHash].exists,  "Hash already registered");

        hashRegistry[msgHash] = HashRecord({
            sender   : msg.sender,
            timestamp: block.timestamp,
            exists   : true
        });
        allHashes.push(msgHash);

        emit HashStored(msgHash, msg.sender, block.timestamp);
    }

    /**
     * @notice Check whether a hash was previously registered.
     * @param  msgHash  32-byte hash to look up
     * @return exists_   true if found
     * @return sender_   address that stored it
     * @return timestamp_ UNIX timestamp of storage
     */
    function checkHash(bytes32 msgHash)
        external
        view
        returns (bool exists_, address sender_, uint256 timestamp_)
    {
        HashRecord storage rec = hashRegistry[msgHash];
        return (rec.exists, rec.sender, rec.timestamp);
    }

    /**
     * @notice Return total number of registered hashes.
     */
    function totalHashes() external view returns (uint256) {
        return allHashes.length;
    }

    /**
     * @notice Get hash at a specific index (for enumeration).
     */
    function getHashAt(uint256 index) external view returns (bytes32) {
        require(index < allHashes.length, "Index out of bounds");
        return allHashes[index];
    }
}
