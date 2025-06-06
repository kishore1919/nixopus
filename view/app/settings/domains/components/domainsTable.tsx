import React from 'react';
import { Domain } from '@/redux/types/domain';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import { DomainTypeTag } from './domain-type-tag';
import { DomainActions } from './domain-actions';
import { useTranslation } from '@/hooks/use-translation';

interface DomainsTableProps {
  domains: Domain[];
}

function DomainsTable({ domains }: DomainsTableProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-secondary shadow-md rounded-lg overflow-hidden p-4">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow>
            <TableHead className="text-xs font-medium text-muted-foreground">
              {t('settings.domains.table.headers.domain')}
            </TableHead>
            <TableHead className="text-xs font-medium text-muted-foreground">
              {t('settings.domains.table.headers.type')}
            </TableHead>
            <TableHead className="text-right text-xs font-medium text-muted-foreground">
              {t('settings.domains.table.headers.actions')}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody className="bg-secondary divide-y divide-border">
          {domains?.flatMap((domain) => (
            <TableRow key={domain.id}>
              <TableCell className="whitespace-nowrap font-medium text-foreground">
                {domain.name}
              </TableCell>
              <TableCell className="whitespace-nowrap text-muted-foreground">
                <DomainTypeTag isWildcard={domain.name.startsWith('*')} />
              </TableCell>
              <TableCell className="whitespace-nowrap text-right">
                <DomainActions domain={domain} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export default DomainsTable;
