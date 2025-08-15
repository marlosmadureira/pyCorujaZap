import httpx
import time
import sys
import os
from typing import List, Dict

# Adicionar o diretório pai ao path (mesmo padrão do extractor.py)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Agora as importações funcionarão
from db.session import get_session
from db.models import IP

class IPEnricher:
    """Classe para enriquecer IPs."""
    
    def __init__(self):
        self.api_url = "http://ip-api.com/batch"
        self.fields = "status,message,continent,country,countryCode,region,regionName,city,district,zip,lat,lon,timezone,isp,org,asname,mobile,query"
        self.batch_size = 100
        self.delay_between_requests = 4  # 4 segundos entre requests (15/min)
    
    def get_pending_ips(self) -> List[str]:
        """Busca TODOS os IPs que ainda não foram enriquecidos."""
        with get_session() as session:
            pending_ips = session.query(IP.sender_ip).filter(
                IP.country.is_(None)  # IPs sem dados geográficos
            ).all()  # REMOVER o .limit(100) para pegar todos
            
            return [ip[0] for ip in pending_ips]
    
    def query_ip_api(self, ip_list: List[str]) -> List[Dict]:
        """Consulta a API para lista de IPs."""
        if not ip_list:
            return []
        
        payload = ip_list
        params = {"fields": self.fields}
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    self.api_url,
                    json=payload,
                    params=params
                )
                response.raise_for_status()
                return response.json()
                
        except Exception as e:
            print(f"Erro na consulta IP: {e}")
            return []
    
    def update_ip_data(self, ip_results: List[Dict]):
        """Atualiza dados dos IPs no banco."""
        with get_session() as session:
            for result in ip_results:
                if result.get('status') == 'success':
                    ip_record = session.query(IP).filter_by(
                        sender_ip=result['query']
                    ).first()
                    
                    if ip_record:
                        # Atualizar com dados da API
                        ip_record.continent = result.get('continent')
                        ip_record.country = result.get('country')
                        ip_record.country_code = result.get('countryCode')
                        ip_record.region = result.get('region')
                        ip_record.region_name = result.get('regionName')
                        ip_record.city = result.get('city')
                        ip_record.district = result.get('district')
                        ip_record.zipcode_ip = result.get('zip')
                        ip_record.latitude = result.get('lat')
                        ip_record.longitude = result.get('lon')
                        ip_record.timezone_ip = result.get('timezone')
                        ip_record.isp = result.get('isp')
                        ip_record.org = result.get('org')
                        ip_record.as_name = result.get('asname')
                        ip_record.mobile = result.get('mobile')
            
            session.commit()
            print(f"{len(ip_results)} IPs atualizados")
    
    def process_pending_ips(self):
        """Processa TODOS os IPs pendentes, dividindo em batches automaticamente."""
        pending_ips = self.get_pending_ips()
        
        if not pending_ips:
            print("Nenhum IP pendente para processar")
            return
        
        total_ips = len(pending_ips)
        print(f"Processando {total_ips} IPs...")
        
        # Calcular número de batches necessários
        total_batches = (total_ips + self.batch_size - 1) // self.batch_size
        print(f"Dividindo em {total_batches} batches de até {self.batch_size} IPs")
        
        # Processar em batches de 100 (limite da API)
        for i in range(0, total_ips, self.batch_size):
            batch = pending_ips[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            
            print(f"Processando batch {batch_num}/{total_batches} ({len(batch)} IPs)")
            
            # Consultar API
            results = self.query_ip_api(batch)
            
            # Atualizar banco
            if results:
                self.update_ip_data(results)
                success_count = len([r for r in results if r.get('status') == 'success'])
                print(f"{success_count}/{len(batch)} IPs do batch processados com sucesso")
            
            # Aguardar entre batches para respeitar rate limit (exceto no último)
            if batch_num < total_batches:
                print(f"Aguardando {self.delay_between_requests}s antes do próximo batch...")
                time.sleep(self.delay_between_requests)
        
        print(f"Processamento concluído! {total_ips} IPs processados em {total_batches} batches")
