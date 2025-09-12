import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from neo4j import GraphDatabase
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Placeholders for server configuration
GRAPH_DB_CONFIG = {
    "uri": "bolt://localhost:7687",  # Replace with your Neo4j URI
    "username": "neo4j",              # Replace with your username
    "password": "password",           # Replace with your password
    "database": "neo4j"               # Replace with your database name
}

@dataclass
class OrganismNode:
    """Data class for Organism nodes"""
    genus: str
    species: str
    infraspecies: str
    datastore_url: str
    node_type: str = "Organism"
    
    @property
    def node_id(self) -> str:
        """Generate unique ID for the organism"""
        return f"{self.genus}.{self.species}.{self.infraspecies}"
    
    @property
    def display_name(self) -> str:
        """Generate display name for the organism"""
        return f"{self.genus} {self.species} {self.infraspecies}".strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j"""
        return {
            "node_id": self.node_id,
            "genus": self.genus,
            "species": self.species,
            "infraspecies": self.infraspecies,
            "datastore_url": self.datastore_url,
            "display_name": self.display_name,
            "node_type": self.node_type
        }

@dataclass
class GenomeNode:
    """Data class for Genome nodes"""
    assembly_id: str
    assembly_name: str
    organism_id: str
    fasta_path: str
    total_length: Optional[int] = None
    num_contigs: Optional[int] = None
    assembly_level: Optional[str] = None
    node_type: str = "Genome"
    
    @property
    def node_id(self) -> str:
        """Generate unique ID for the genome"""
        return self.assembly_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j"""
        data = {
            "node_id": self.node_id,
            "assembly_id": self.assembly_id,
            "assembly_name": self.assembly_name,
            "organism_id": self.organism_id,
            "fasta_path": self.fasta_path,
            "node_type": self.node_type
        }
        # Add optional fields if they exist
        if self.total_length is not None:
            data["total_length"] = self.total_length
        if self.num_contigs is not None:
            data["num_contigs"] = self.num_contigs
        if self.assembly_level is not None:
            data["assembly_level"] = self.assembly_level
        return data

@dataclass
class GeneNode:
    """Data class for Gene nodes"""
    gene_id: str
    gene_name: str
    sequence_id: str
    start: int
    end: int
    strand: str
    gene_type: Optional[str] = None
    biotype: Optional[str] = None
    genome_id: Optional[str] = None
    node_type: str = "Gene"
    
    @property
    def node_id(self) -> str:
        """Generate unique ID for the gene"""
        return f"{self.genome_id}:{self.gene_id}" if self.genome_id else self.gene_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j"""
        data = {
            "node_id": self.node_id,
            "gene_id": self.gene_id,
            "gene_name": self.gene_name,
            "sequence_id": self.sequence_id,
            "start": self.start,
            "end": self.end,
            "strand": self.strand,
            "node_type": self.node_type
        }
        if self.gene_type:
            data["gene_type"] = self.gene_type
        if self.biotype:
            data["biotype"] = self.biotype
        if self.genome_id:
            data["genome_id"] = self.genome_id
        return data

class GenomicGraphParser:
    """Parser for loading genomic data into a graph database"""
    
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """Initialize the parser with database connection"""
        self.uri = uri or GRAPH_DB_CONFIG["uri"]
        self.username = username or GRAPH_DB_CONFIG["username"]
        self.password = password or GRAPH_DB_CONFIG["password"]
        self.driver = None
        
    def connect(self):
        """Establish connection to the graph database"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password)
            )
            self.driver.verify_connectivity()
            logger.info("Successfully connected to graph database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close the database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    def parse_organism_json(self, json_data: Dict[str, str]) -> OrganismNode:
        """Parse organism JSON data into OrganismNode"""
        try:
            organism = OrganismNode(
                genus=json_data.get("genus", ""),
                species=json_data.get("species", ""),
                infraspecies=json_data.get("infraspecies", ""),
                datastore_url=json_data.get("datastore_url", "")
            )
            logger.info(f"Parsed organism: {organism.display_name}")
            return organism
        except Exception as e:
            logger.error(f"Error parsing organism JSON: {e}")
            raise
    
    def parse_genome_json(self, json_data: Dict[str, Any]) -> GenomeNode:
        """Parse genome JSON data into GenomeNode"""
        try:
            genome = GenomeNode(
                assembly_id=json_data.get("assembly_id", ""),
                assembly_name=json_data.get("assembly_name", ""),
                organism_id=json_data.get("organism_id", ""),
                fasta_path=json_data.get("fasta_path", ""),
                total_length=json_data.get("total_length"),
                num_contigs=json_data.get("num_contigs"),
                assembly_level=json_data.get("assembly_level")
            )
            logger.info(f"Parsed genome: {genome.assembly_id}")
            return genome
        except Exception as e:
            logger.error(f"Error parsing genome JSON: {e}")
            raise
    
    def parse_gene_json(self, json_data: Dict[str, Any]) -> GeneNode:
        """Parse gene JSON data into GeneNode"""
        try:
            gene = GeneNode(
                gene_id=json_data.get("gene_id", ""),
                gene_name=json_data.get("gene_name", ""),
                sequence_id=json_data.get("sequence_id", ""),
                start=int(json_data.get("start", 0)),
                end=int(json_data.get("end", 0)),
                strand=json_data.get("strand", "+"),
                gene_type=json_data.get("gene_type"),
                biotype=json_data.get("biotype"),
                genome_id=json_data.get("genome_id")
            )
            logger.info(f"Parsed gene: {gene.gene_id}")
            return gene
        except Exception as e:
            logger.error(f"Error parsing gene JSON: {e}")
            raise
    
    def load_json_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Load JSON data from file"""
        try:
            path = Path(filepath)
            with open(path, 'r') as f:
                data = json.load(f)
            
            # Handle both single object and array of objects
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                raise ValueError(f"Unexpected JSON structure in {filepath}")
                
        except Exception as e:
            logger.error(f"Error loading JSON file {filepath}: {e}")
            raise
    
    def create_organism_node(self, organism: OrganismNode):
        """Create an organism node in the graph database"""
        with self.driver.session() as session:
            query = """
            MERGE (o:Organism {node_id: $node_id})
            SET o += $properties
            RETURN o
            """
            result = session.run(query, 
                node_id=organism.node_id,
                properties=organism.to_dict()
            )
            logger.info(f"Created/updated organism node: {organism.node_id}")
            return result.single()
    
    def create_genome_node(self, genome: GenomeNode):
        """Create a genome node in the graph database"""
        with self.driver.session() as session:
            query = """
            MERGE (g:Genome {node_id: $node_id})
            SET g += $properties
            RETURN g
            """
            result = session.run(query,
                node_id=genome.node_id,
                properties=genome.to_dict()
            )
            logger.info(f"Created/updated genome node: {genome.node_id}")
            return result.single()
    
    def create_gene_node(self, gene: GeneNode):
        """Create a gene node in the graph database"""
        with self.driver.session() as session:
            query = """
            MERGE (g:Gene {node_id: $node_id})
            SET g += $properties
            RETURN g
            """
            result = session.run(query,
                node_id=gene.node_id,
                properties=gene.to_dict()
            )
            logger.info(f"Created/updated gene node: {gene.node_id}")
            return result.single()
    
    def create_organism_genome_relationship(self, organism_id: str, genome_id: str):
        """Create HAS_GENOME relationship between organism and genome"""
        with self.driver.session() as session:
            query = """
            MATCH (o:Organism {node_id: $organism_id})
            MATCH (g:Genome {node_id: $genome_id})
            MERGE (o)-[r:HAS_GENOME]->(g)
            RETURN o, r, g
            """
            result = session.run(query,
                organism_id=organism_id,
                genome_id=genome_id
            )
            logger.info(f"Created relationship: {organism_id} -[:HAS_GENOME]-> {genome_id}")
            return result.single()
    
    def create_gene_location_relationship(self, gene_id: str, sequence_id: str, 
                                        start: int, end: int, strand: str):
        """Create LOCATED_ON relationship between gene and sequence"""
        with self.driver.session() as session:
            query = """
            MATCH (g:Gene {node_id: $gene_id})
            MATCH (s:Sequence {sequence_id: $sequence_id})
            MERGE (g)-[r:LOCATED_ON {start: $start, end: $end, strand: $strand}]->(s)
            RETURN g, r, s
            """
            result = session.run(query,
                gene_id=gene_id,
                sequence_id=sequence_id,
                start=start,
                end=end,
                strand=strand
            )
            logger.info(f"Created relationship: {gene_id} -[:LOCATED_ON]-> {sequence_id}")
            return result.single()
    
    def batch_create_nodes(self, nodes: List[Any], batch_size: int = 1000):
        """Batch create nodes for better performance"""
        node_type = type(nodes[0]).__name__
        
        with self.driver.session() as session:
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i:i + batch_size]
                
                if isinstance(batch[0], OrganismNode):
                    query = """
                    UNWIND $nodes AS node
                    MERGE (o:Organism {node_id: node.node_id})
                    SET o += node
                    """
                elif isinstance(batch[0], GenomeNode):
                    query = """
                    UNWIND $nodes AS node
                    MERGE (g:Genome {node_id: node.node_id})
                    SET g += node
                    """
                elif isinstance(batch[0], GeneNode):
                    query = """
                    UNWIND $nodes AS node
                    MERGE (g:Gene {node_id: node.node_id})
                    SET g += node
                    """
                else:
                    raise ValueError(f"Unknown node type: {node_type}")
                
                session.run(query, nodes=[n.to_dict() for n in batch])
                logger.info(f"Created batch of {len(batch)} {node_type} nodes")
    
    def create_indexes(self):
        """Create indexes for better query performance"""
        with self.driver.session() as session:
            indexes = [
                "CREATE INDEX organism_id_idx IF NOT EXISTS FOR (o:Organism) ON (o.node_id)",
                "CREATE INDEX organism_taxonomy_idx IF NOT EXISTS FOR (o:Organism) ON (o.genus, o.species)",
                "CREATE INDEX genome_id_idx IF NOT EXISTS FOR (g:Genome) ON (g.node_id)",
                "CREATE INDEX genome_assembly_idx IF NOT EXISTS FOR (g:Genome) ON (g.assembly_id)",
                "CREATE INDEX gene_id_idx IF NOT EXISTS FOR (g:Gene) ON (g.node_id)",
                "CREATE INDEX gene_name_idx IF NOT EXISTS FOR (g:Gene) ON (g.gene_name)",
                "CREATE INDEX gene_genome_idx IF NOT EXISTS FOR (g:Gene) ON (g.genome_id)"
            ]
            
            for index_query in indexes:
                try:
                    session.run(index_query)
                    logger.info(f"Created index: {index_query}")
                except Exception as e:
                    logger.warning(f"Index creation skipped (may already exist): {e}")


# Example usage
if __name__ == "__main__":
    # Example organism JSON
    organism_json = {
        "genus": "Escherichia",
        "species": "coli",
        "infraspecies": "K-12",
        "datastore_uri": "https://example.com/data/ecoli_k12",
        "readme_uri": "https://example.com/readme/ecoli_k12.md"
    }
    
    # Initialize parser with placeholders
    with GenomicGraphParser(
        uri="bolt://localhost:7687",
        username="your_username",
        password="your_password"
    ) as parser:
        
        # Create indexes
        parser.create_indexes()
        
        # Parse and create organism node
        organism = parser.parse_organism_json(organism_json)
        parser.create_organism_node(organism)
        
        # Example: Load organisms from file
        # organisms_data = parser.load_json_file("organisms.json")
        # organisms = [parser.parse_organism_json(data) for data in organisms_data]
        # parser.batch_create_nodes(organisms)

