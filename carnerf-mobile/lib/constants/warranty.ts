export interface WarrantyTerms {
  general: { years: number; km: number };
  powertrain: { years: number; km: number };
  rust?: { years: number; km: number };
}

const UNLIMITED_KM = 999_999;

export const WARRANTY_BY_BRAND: Record<string, WarrantyTerms> = {
  현대: {
    general: { years: 3, km: 60000 },
    powertrain: { years: 5, km: 100000 },
    rust: { years: 5, km: UNLIMITED_KM },
  },
  기아: {
    general: { years: 3, km: 60000 },
    powertrain: { years: 5, km: 100000 },
    rust: { years: 5, km: UNLIMITED_KM },
  },
  제네시스: {
    general: { years: 5, km: 100000 },
    powertrain: { years: 5, km: 100000 },
    rust: { years: 7, km: UNLIMITED_KM },
  },
  쉐보레: {
    general: { years: 5, km: 100000 },
    powertrain: { years: 5, km: 100000 },
  },
  BMW: {
    general: { years: 3, km: UNLIMITED_KM },
    powertrain: { years: 3, km: UNLIMITED_KM },
  },
  벤츠: {
    general: { years: 3, km: UNLIMITED_KM },
    powertrain: { years: 3, km: UNLIMITED_KM },
  },
  아우디: {
    general: { years: 3, km: UNLIMITED_KM },
    powertrain: { years: 3, km: UNLIMITED_KM },
  },
  렉서스: {
    general: { years: 4, km: 100000 },
    powertrain: { years: 6, km: 120000 },
  },
  포르쉐: {
    general: { years: 4, km: UNLIMITED_KM },
    powertrain: { years: 4, km: UNLIMITED_KM },
  },
};

export const INSPECTION_WARRANTY = { days: 30, km: 2000 };
